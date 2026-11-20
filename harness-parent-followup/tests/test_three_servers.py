"""Replay the three-server archive through the revised Agent.

Each test restarts the Agent after the first k complete rounds of a real run (same bridge-visible cells,
organizer partition diagnostics, sources and lineage as recorded) and inspects the next plan request,
the search log and the returned candidate. No model call reaches a gateway and no physical job runs.

    python3 -I -B -m unittest discover -s tests -v

Run the same command inside the contest image (Python 3.8) before a formal run; see REVIEW.md section 8.
"""

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stubs

RUNS = json.loads((HERE / "fixtures" / "three_servers.json").read_text())
ORIGINAL, PANEL, EVIDENCE = RUNS["claude-original"], RUNS["claude-new"], RUNS["ours-new"]
PANEL_CELLS = [{"case": cell["case"], "seed": cell["seed"]} for cell in PANEL[0]["cells"]]


def gate_module():
    spec = importlib.util.spec_from_file_location("py38_gate", HERE.parent / "tools" / "py38_gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replay(rounds, opening, cells=None, labels=None, limit=10, patch=None):
    """Restart after `rounds`; return (first plan request or None, returned ID, search-log events)."""
    folder = stubs.workdir()
    try:
        events = [{"event": "submitted", "request_id": row["request_id"], "decision": row["decision"],
                   **row["attempt"]} for row in rounds]
        agent, copy = stubs.load_agent(folder, opening=opening, log_events=events)
        if patch:
            patch(agent)
        receipts = [{"request_id": row["request_id"], "candidate_id": row["candidate_id"], "status": row["status"],
                     "source": row["source"], "reason": None, "partition": row["partition"],
                     "labels": (labels or {}).get(row["request_id"], {}),
                     "feedback": {"score": row["score"], "cells": row["cells"]}} for row in rounds]
        bridge = stubs.Bridge(folder, lambda bridge, system, request: stubs.completed("Plan."),
                              receipts=receipts, model_limit=1, evaluation_limit=limit, cells=cells)
        bridge.baseline_candidate = rounds[0]["attempt"]["parent_id"]
        returned = agent.Agent().run(bridge)
        request = bridge.requests[0]["request"] if bridge.requests else None
        log = [json.loads(line) for line in (copy / "search.jsonl").read_text().splitlines() if line.strip()]
        return request, returned, log
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def find_summary(request, candidate_id):
    """The receipt summary of one candidate wherever the request shows it."""
    rows = [request.get("parent_feedback"), request.get("incumbent_feedback"), *request.get("recent_feedback", [])]
    return next(row for row in rows if row and row["candidate_id"] == candidate_id)


def synthetic_labels(parent_round, child_round, moved):
    """Label files for two rounds: each cell has 400 instances and the child moves `moved[key]` of them."""
    files = {parent_round["request_id"]: {}, child_round["request_id"]: {}}
    for cell in parent_round["cells"]:
        key = f"{cell['case']}/{cell['seed']}"
        names = [f"u{index:04d}" for index in range(400)]
        parent = ["top" if index % 2 else "bottom" for index in range(400)]
        child = list(parent)
        for index in range(moved[key]):
            child[index] = "bottom" if child[index] == "top" else "top"
        files[parent_round["request_id"]][key] = list(zip(names, parent))
        files[child_round["request_id"]][key] = list(zip(names, child))
    return files


class OriginalRunDuplicates(unittest.TestCase):
    """Round 6 rewrote round 4's decoder; all nine cells repeat round 4 bit for bit."""

    def test_round_6_is_a_duplicate_outcome_of_round_4(self):
        request, _, _ = replay(ORIGINAL[:6], "decoder_only")
        decision = request["decision"]
        self.assertEqual(decision.get("reason"), "duplicate_outcome", decision)
        self.assertEqual(decision.get("same_as"), ORIGINAL[3]["candidate_id"])
        trial = next(row for row in request["prior_trials"] if row["candidate_id"] == ORIGINAL[5]["candidate_id"])
        self.assertEqual(trial["evidence"]["reason"], "duplicate_outcome")

    def test_the_next_hypothesis_does_not_build_on_the_duplicate(self):
        request, _, _ = replay(ORIGINAL[:6], "decoder_only")
        self.assertNotIn(request["parent_id"], (ORIGINAL[3]["candidate_id"], ORIGINAL[5]["candidate_id"]))
        self.assertEqual(request["search_intent"], "loss_only")  # round 6 edited the decoder


class FinalSelection(unittest.TestCase):

    def test_original_run_keeps_round_4_by_the_robust_rule(self):
        _, returned, log = replay(ORIGINAL, "decoder_only")
        self.assertEqual(returned, ORIGINAL[3]["candidate_id"])
        selected = [event for event in log if event["event"] == "selected"][-1]
        self.assertEqual(selected["selection"]["rule"], "largest_gain_without_best_cell", selected["selection"])
        rows = {row["candidate_id"]: row for row in selected["selection"]["candidates"]}
        self.assertTrue(rows[ORIGINAL[3]["candidate_id"]]["eligible"])
        self.assertEqual(rows[ORIGINAL[3]["candidate_id"]]["best_cell"]["case"], "ariane133-ng45")

    def test_panel_gain_carried_by_one_cell_is_not_eligible(self):
        _, returned, log = replay(PANEL, "loss_only", cells=PANEL_CELLS, limit=3)
        self.assertEqual(returned, PANEL[2]["candidate_id"])  # still the highest official score
        selected = [event for event in log if event["event"] == "selected"][-1]
        self.assertEqual(selected["selection"]["rule"], "highest_official_score", selected["selection"])
        rows = {row["candidate_id"]: row for row in selected["selection"]["candidates"]}
        third = rows[PANEL[2]["candidate_id"]]
        self.assertFalse(third["eligible"])
        self.assertEqual((third["best_cell"]["case"], third["improved_cases"]), ("ariane133-ng45", 1))


class EvidenceRunCrashPath(unittest.TestCase):
    """The evidence-driven run crashed comparing round 4 with its candidate parent, round 3."""

    def labels(self):
        moved = {f"{cell['case']}/{cell['seed']}": index * 3 for index, cell in enumerate(EVIDENCE[2]["cells"])}
        return moved, synthetic_labels(EVIDENCE[2], EVIDENCE[3], moved)

    def test_assignment_change_from_a_candidate_parent_is_measured(self):
        moved, labels = self.labels()
        request, returned, log = replay(EVIDENCE, "decoder_only", labels=labels)
        self.assertFalse([event for event in log if event["event"] in ("analysis_error", "agent_error")], log)
        summary = find_summary(request, EVIDENCE[3]["candidate_id"])
        cells = {(cell["case"], cell["seed"]): cell for cell in summary["parent_comparison"]["cells"]}
        for key, count in moved.items():
            case, seed = key.split("/")
            change = cells[case, seed]["assignment_vs_parent"]
            self.assertEqual(change["changed_count"], count, (key, change))
            self.assertFalse(change["die_exchange"])
        self.assertIn("feasible_cut_net_count_delta", cells["bp-ng45", "1001"])

    def test_an_analysis_crash_does_not_end_the_run(self):
        def broken(agent):
            # The same failure the container raised, injected into a function every version calls.
            def comparison(*args, **kwargs):
                raise AttributeError("'int' object has no attribute 'bit_count'")
            agent.comparison_for_prompt = comparison

        _, labels = self.labels()
        request, returned, log = replay(EVIDENCE, "decoder_only", labels=labels, patch=broken)
        self.assertIsNotNone(request, "the search must continue to the next proposal")
        self.assertTrue([event for event in log if event["event"] == "analysis_error"])
        self.assertIn(returned, {row["candidate_id"] for row in EVIDENCE})


class EvidenceRunDecisions(unittest.TestCase):
    """What the revised rules decide on the evidence-driven run's real receipts."""

    def test_weak_loss_edit_is_strengthened_not_abandoned(self):
        request, _, _ = replay(EVIDENCE[:2], "decoder_only", limit=3)
        self.assertEqual(request["decision"]["reason"], "partition_mostly_unchanged", request["decision"])
        self.assertEqual(request["search_intent"], "loss_only")
        self.assertEqual(request["start_reference"]["same_host_cells"], 6)

    def test_round_3_is_not_repaired_against_an_unmeasured_start_cell(self):
        # The recorded run repaired bp_fe-ng45/1001 (-33 against the published start, never measured here).
        request, _, _ = replay(EVIDENCE[:3], "decoder_only", limit=4)
        self.assertNotEqual(request["search_intent"], "repair", request["decision"])
        self.assertEqual(request["prior_trials"][-1]["evidence"]["reason"], "narrow_gain")
        self.assertEqual(request["decision"]["reason"], "follow_up_case_champion")
        self.assertEqual(request["parent_id"], EVIDENCE[2]["candidate_id"])


class ContainerPython(unittest.TestCase):
    def test_only_plans_for_the_exact_parent_and_intent_are_used(self):
        folder = stubs.workdir()
        try:
            agent, _ = stubs.load_agent(folder)
            packet = {"parent_id": "p", "search_intent": "decoder_only", "plan": "Change the area sweep."}
            self.assertEqual(agent.bound_plan(json.dumps(packet), "p", "decoder_only"), packet["plan"])
            for raw in (json.dumps(dict(packet, parent_id="comparison")),
                        json.dumps(dict(packet, search_intent="loss_only")), "Unbound plan"):
                self.assertEqual(agent.bound_plan(raw, "p", "decoder_only"), "")
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_followup_is_consumed_by_a_child_of_the_champion(self):
        request, _, _ = replay(EVIDENCE[:3], "decoder_only")
        parent = request["parent_feedback"]
        folder = stubs.workdir()
        try:
            agent, _ = stubs.load_agent(folder)
            best = EVIDENCE[2]
            child = {"request_id": "child", "attempt": {"parent_id": best["candidate_id"],
                                                        "changed_components": {"decoder": "area sweep"}}}
            self.assertIsNotNone(agent.case_followup(best, [parent]))
            self.assertIsNone(agent.case_followup(best, [parent, child]))
        finally:
            shutil.rmtree(folder, ignore_errors=True)


    def test_agent_source_passes_the_python_38_gate(self):
        gate = gate_module()
        findings = [(path.name, finding) for path in sorted(stubs.AGENT_DIR.rglob("*.py")) for finding in gate.scan(path)]
        self.assertEqual(findings, [])

    def test_gate_flags_the_bit_count_call_that_crashed_the_evidence_run(self):
        gate = gate_module()
        sample = Path(stubs.workdir()) / "sample.py"
        sample.write_text("def moved(a, b):\n    return (a ^ b).bit_count()\n", encoding="utf-8")
        try:
            self.assertEqual([label for _, label in gate.scan(sample)], ["int.bit_count (3.10)"])
        finally:
            shutil.rmtree(sample.parent, ignore_errors=True)

    def test_candidate_gate_rejects_syntax_newer_than_38(self):
        folder = stubs.workdir()
        try:
            agent, _ = stubs.load_agent(folder)
            newer = stubs.variant(decoder_body="    match seed:\n        case _:\n            pass\n"
                                               "    return reference_global_two_way(embeddings, node_areas, seed, "
                                               "max_iterations, balance_target)")
            with self.assertRaises(ValueError):
                agent.candidate_gate(newer)
            agent.candidate_gate(stubs.INITIAL)
        finally:
            shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
