"""End-to-end replay of the patched branching Agent.run() through the offline bridge stand-in.

These tests run the team's agent.py, search_control.py, paired_feedback.py and candidate_reply.py with
the new ledger, rolling_plan and self_test modules. They restart the Agent after k real rounds of an
archived run (official cells, organizer partition diagnostics, accepted sources and lineage) and
script the model's replies. No gateway, bridge socket or physical job is involved.

    python3 -I -B -m unittest discover -s tests -p "test_agent_integration.py" -v

Set DUMP_REQUESTS=<folder> to save every model request each test sends (the exact generation and
planning payloads). Run the same command under the contest image's Python 3.8 before a formal run.
"""

import ast
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stubs  # noqa: E402

RUNS = json.loads((HERE / "fixtures" / "three_servers.json").read_text(encoding="utf-8"))
ORIGINAL, EVIDENCE = RUNS["claude-original"], RUNS["ours-new"]
HYPOTHESIS = ("Mechanism: {m}; Decision: {d}; Prediction: {p}; Falsifier: {f}")
DOC_DECODER = '    """' + HYPOTHESIS.format(
    m="exchange the two dies of the reference grouping", d="every group changes tier",
    p="TNS changes where critical paths cross the boundary", f="paired TNS is unchanged on most cells") + '"""\n'
DOC_LOSS = '    """' + HYPOTHESIS.format(
    m="weaken the negative-pair repulsion", d="boundary groups move toward their neighbours",
    p="fewer timing-critical nets cross the dies", f="TNS does not improve on most seeds") + '"""\n'
HELPER = "reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)"
EXCHANGE = stubs.variant(decoder_body=DOC_DECODER + "    labels = " + HELPER + "\n    return 1 - labels")
SEED_RULE = stubs.variant(decoder_body=DOC_DECODER + "    labels = " + HELPER + "\n    if seed == 1002:\n"
                                       "        return 1 - labels\n    return labels")
LOSS_EDIT = stubs.variant(loss_body=DOC_LOSS + "    return -(\n        F.logsigmoid(positive_scores).sum()\n"
                                    "        + 0.9 * F.logsigmoid(-negative_scores).sum()\n"
                                    "    ) / max(1, source_batch_size)")


def segment(source, index):
    node = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)][index]
    return "\n".join(source.splitlines()[node.lineno - 1:node.end_lineno])


def combine(loss_program, decoder_program):
    """The loss text of one program with the decoder text of another (what a one-function reply returns)."""
    return ("# EVOLVE-BLOCK-START\n" + segment(loss_program, 0) + "\n\n\n" + segment(decoder_program, 1)
            + "\n# EVOLVE-BLOCK-END\n")


def scripted(*texts):
    queue = list(texts)

    def reply(bridge, system, request):
        if not queue:
            raise AssertionError("Unexpected model call: " + system[:60])
        return stubs.completed(queue.pop(0))
    return reply


def echo(row, shift=-1.0):
    """An evaluation callback that returns a real round's cells, shifted, under a new candidate ID."""
    def evaluate(bridge, source, request_id):
        return {"candidate_id": "cand-" + request_id[2:14], "status": "succeeded", "reason": None,
                "partition": row["partition"], "feedback": {"score": row["score"] + shift, "cells": [
                    {**cell, "score": cell["score"] + shift} for cell in row["cells"]]}}
    return evaluate


def run_agent(rows, reply, evaluate=None, limit=None, patch=None, name=None, checkpoint=None):
    """Restart after `rows`; return (bridge, returned ID, search-log events, saved program.py)."""
    folder = stubs.workdir()
    try:
        events = [{"event": "submitted", "request_id": row["request_id"], "decision": row.get("decision"),
                   **row["attempt"]} for row in rows]
        agent, copy_dir = stubs.load_agent(folder, log_events=events)
        if patch:
            patch(agent)
        receipts = [{"request_id": row["request_id"], "candidate_id": row["candidate_id"], "status": row["status"],
                     "source": row["source"], "reason": None, "partition": row["partition"],
                     "feedback": {"score": row["score"], "cells": row["cells"]}} for row in rows]
        bridge = stubs.Bridge(folder, reply, evaluate=evaluate, receipts=receipts,
                              evaluation_limit=limit or len(rows) + 1)
        bridge.baseline_candidate = rows[0]["attempt"]["parent_id"]
        if checkpoint is not None:
            (Path(bridge.files["workspaces"]) / "search-branch.json").write_text(json.dumps(checkpoint))
        returned = agent.Agent().run(bridge)
        log = [json.loads(line) for line in (copy_dir / "search.jsonl").read_text().splitlines() if line.strip()]
        program = (copy_dir / "program.py").read_text(encoding="utf-8") if (copy_dir / "program.py").exists() else None
        if os.environ.get("DUMP_REQUESTS") and name:
            target = Path(os.environ["DUMP_REQUESTS"])
            target.mkdir(parents=True, exist_ok=True)
            (target / (name + ".json")).write_text(json.dumps(bridge.requests, indent=1, ensure_ascii=False),
                                                   encoding="utf-8")
            kept = [event for event in log if event["event"] in ("plan", "submitted", "invalid_proposal",
                                                                 "official_receipt", "runtime_capabilities")]
            (target / (name + ".log.json")).write_text(json.dumps(kept, indent=1, ensure_ascii=False), encoding="utf-8")
        return bridge, returned, log, program
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def events(log, name):
    return [event for event in log if event["event"] == name]


def removal_receipt(delta):
    """The removal splice of round 5 as an earlier process would have recorded it (a hypothetical outcome)."""
    sys.path.insert(0, str(stubs.AGENT_DIR))
    import ledger as L
    import rolling_plan as P
    import replay
    rows = ORIGINAL[:4]
    evidence = replay.ledger_for(rows)
    plan = P.plan_next(evidence, replay.baseline("claude-original", 4), 6, 10,
                       {(f["loss"], f["decoder"]) for f in (L.factor_ids(row["source"]) for row in rows)})
    choice = plan["choice"]
    assert choice["kind"] == "removal", choice
    row = copy.deepcopy(ORIGINAL[3])
    row.update(round=5, request_id="e-removal-of-r4-loss", candidate_id="cand-removal-r4",
               source=P.splice_source(stubs.INITIAL, ORIGINAL[3]["source"]))
    for cell in row["cells"]:
        cell["score"] += delta
    row["score"] += delta
    row["attempt"] = {"parent_id": ORIGINAL[3]["candidate_id"], "search_intent": "loss_only", "policy_action": "removal",
                      "changed_components": {"loss": P.splice_hypothesis(choice)},
                      "experiment": {key: choice.get(key) for key in ("id", "kind", "parent", "parent_candidate",
                                                                      "component", "question", "contract", "factors",
                                                                      "donors")}}
    row["decision"] = {"reason": "extend_best", "component": "loss"}
    return row


class ControlsEndToEnd(unittest.TestCase):

    def test_fork_reuses_first_two_and_selects_global_best_without_recharging_old_rows(self):
        rows = copy.deepcopy(ORIGINAL[:4])
        rows[2]["score"] = 99.0
        checkpoint = {"keep": [r["request_id"] for r in rows[:2]], "superseded": [r["request_id"] for r in rows[2:]]}
        def reply(bridge, system, request):
            if "parent_program" not in request:
                return stubs.completed("{}")
            parent = request["parent_program"]
            if request["search_intent"] == "loss_only":
                return stubs.completed(combine(LOSS_EDIT, parent))
            return stubs.completed(combine(parent, EXCHANGE))
        bridge, selected, log, _ = run_agent(rows, reply, evaluate=echo(rows[0]), limit=5, checkpoint=checkpoint)
        self.assertEqual(len(bridge.order), 5)
        self.assertEqual(bridge.order[:4], checkpoint["keep"] + checkpoint["superseded"])
        self.assertEqual(events(log, "branch_resumed")[0]["logical_next"], 3)
        self.assertEqual(len(bridge.generations()[0]["request"]["prior_trials"]), 2)
        self.assertEqual(selected, rows[2]["candidate_id"])

    def test_missing_control_is_assembled_and_submitted_exactly_once(self):
        follow_up = combine(LOSS_EDIT, ORIGINAL[3]["source"])  # a loss edit on the removal program (start loss + R4 decoder)
        bridge, returned, log, _ = run_agent(ORIGINAL[:4], scripted(follow_up), evaluate=echo(ORIGINAL[3]), limit=6,
                                             name="missing_control")
        submitted = events(log, "submitted")[-2:]
        self.assertEqual([row["policy_action"] for row in submitted], ["removal", "removal_follow_up"])
        removal_id = submitted[0]["request_id"]
        self.assertEqual(sum(1 for rid in bridge.order if rid == removal_id), 1)
        self.assertEqual(len(bridge.requests), 1)  # the splice used no model call
        request = bridge.requests[0]["request"]
        self.assertEqual(request["parent_id"], bridge.records[removal_id]["candidate_id"])  # within tolerance
        self.assertEqual(request["search_intent"], "loss_only")
        source = bridge.records[removal_id]["source"]
        self.assertIn("negative-sampling objective", source)   # the start loss
        self.assertIn("int(seed) % max(1, n_nodes)", source)   # R4's decoder
        order = [event["event"] for event in log if event.get("request_id") == removal_id]
        self.assertLess(order.index("official_receipt"), order.index("evaluated"))
        self.assertEqual(returned, ORIGINAL[3]["candidate_id"])

    def test_an_old_control_is_found_after_a_restart_and_reused(self):
        removal = removal_receipt(-20.0)  # measured by an earlier process; R4 needs its loss change
        bridge, _, log, _ = run_agent(ORIGINAL[:4] + [removal], scripted(combine(ORIGINAL[3]["source"], EXCHANGE)),
                                      evaluate=echo(ORIGINAL[3]), limit=6, name="old_control")
        self.assertEqual(len(bridge.order), 6)  # one new evaluation, and it is not the removal again
        new = bridge.records[bridge.order[-1]]
        self.assertNotEqual(new["source"], removal["source"])
        request = bridge.requests[0]["request"]
        self.assertEqual((request["parent_id"], request["search_intent"]), (ORIGINAL[3]["candidate_id"], "decoder_only"))
        lessons = {row["finding"]: row for row in request["experiment"]["lessons"]}
        self.assertIn("needs its loss change", lessons["removal"]["conclusion"])
        self.assertIn("R4-R5", [row["evidence"] for row in request["experiment"]["comparisons"]])
        plan = events(log, "plan")[0]
        self.assertEqual(plan["kind"], "edit")

    def test_label_fingerprint_failure_degrades_without_losing_the_round(self):
        def broken(agent):
            def fail(*args, **kwargs):
                raise OSError("label file unreadable")
            agent.assignment_fingerprints = fail
        follow_up = combine(LOSS_EDIT, ORIGINAL[3]["source"])
        _, _, log, _ = run_agent(ORIGINAL[:4], scripted(follow_up), evaluate=echo(ORIGINAL[3]), limit=6, patch=broken)
        self.assertTrue([e for e in events(log, "feedback_degraded") if e["reason"] == "label fingerprints unavailable"])
        self.assertEqual([e.get("policy_action") for e in events(log, "submitted")[-2:]], ["removal", "removal_follow_up"])

    def test_no_removal_without_a_later_slot_to_act_on_it(self):
        bridge, _, log, _ = run_agent(ORIGINAL[:4], scripted(combine(LOSS_EDIT, ORIGINAL[3]["source"])),
                                      evaluate=echo(ORIGINAL[3]), limit=5)
        self.assertEqual(events(log, "plan")[0]["kind"], "edit")  # one slot left: a removal could not be acted on
        self.assertEqual(len(bridge.requests), 1)


class PreflightAndFeedback(unittest.TestCase):

    def test_failed_preflight_spends_no_evaluation_slot(self):
        parent = EVIDENCE[2]["source"]
        bridge, _, log, _ = run_agent(EVIDENCE[:3], scripted(combine(parent, SEED_RULE), combine(parent, EXCHANGE)),
                                      evaluate=echo(EVIDENCE[2]), limit=4, name="preflight")
        rejected = events(log, "invalid_proposal")
        self.assertEqual(len(rejected), 1)
        self.assertIn("identity_rules", rejected[0]["reason"])
        self.assertIn("Preflight failed", bridge.requests[1]["request"]["previous_generation_issue"])
        self.assertEqual(len(bridge.order), 4)  # three replayed receipts and one new evaluation
        self.assertEqual(len(events(log, "submitted")) - 3, 1)

    def test_optional_feedback_failure_after_a_valid_score_keeps_the_score_and_the_best(self):
        replayed = {row["request_id"] for row in EVIDENCE[:3]}

        def broken(agent):
            original = agent.published_partition_changes

            def flaky(result, root):
                if result["request_id"] not in replayed:
                    raise AttributeError("'int' object has no attribute 'bit_count'")
                return original(result, root)
            agent.published_partition_changes = flaky
        parent = EVIDENCE[2]["source"]
        bridge, returned, log, program = run_agent(EVIDENCE[:3], scripted(combine(parent, EXCHANGE)),
                                                   evaluate=echo(EVIDENCE[2], shift=5.0), limit=4, patch=broken)
        new_id = bridge.order[-1]
        order = [event["event"] for event in log if event.get("request_id") == new_id]
        self.assertLess(order.index("official_receipt"), order.index("feedback_degraded"))
        receipt = next(event for event in log if event["event"] == "official_receipt" and event["request_id"] == new_id)
        self.assertAlmostEqual(receipt["score"], EVIDENCE[2]["score"] + 5.0)
        self.assertEqual(returned, bridge.records[new_id]["candidate_id"])  # the new best is selected
        self.assertEqual(program.strip(), bridge.records[new_id]["source"].strip())  # and saved before analysis failed
        self.assertFalse(events(log, "agent_error"))


class GenerationRequest(unittest.TestCase):

    def test_request_carries_the_contract_and_drops_repeated_views(self):
        parent = EVIDENCE[2]["source"]
        bridge, _, log, _ = run_agent(EVIDENCE[:3], scripted(combine(parent, EXCHANGE)), evaluate=echo(EVIDENCE[2]),
                                      limit=4, name="contract_request")
        request = bridge.requests[0]["request"]
        self.assertEqual(request["search_intent"], "decoder_only")
        contract = request["experiment"]["contract"]
        self.assertEqual(contract["target"]["case"], "bp_fe-ng45")
        self.assertEqual(sorted(rule["case"] for rule in contract["protect"]), ["ariane133-ng45", "bp-ng45"])
        self.assertEqual(len(request["experiment"]["experiment"]["hypotheses"]), 2)
        self.assertNotIn("decision_evidence", request)
        self.assertEqual(len(request["last_trial"]["cells"]), 9)
        self.assertLess(len(json.dumps(request, ensure_ascii=False)), 20000)
        submitted = events(log, "submitted")[-1]
        self.assertEqual(submitted["experiment"]["kind"], "edit")
        self.assertEqual([row for row in submitted["preflight"]["static"] if row["status"] == "fail"], [])
        capabilities = events(log, "runtime_capabilities")[0]
        self.assertIn("decoder_probe", capabilities)

    def test_planner_failure_falls_back_to_the_branching_decision(self):
        def broken(agent):
            def fail(*args, **kwargs):
                raise KeyError("ledger")
            agent.rolling_plan.plan_next = fail
        parent = EVIDENCE[2]["source"]
        bridge, _, log, _ = run_agent(EVIDENCE[:3], scripted(combine(parent, EXCHANGE)), evaluate=echo(EVIDENCE[2]),
                                      limit=4, patch=broken)
        self.assertTrue(events(log, "plan_degraded"))
        self.assertNotIn("experiment", bridge.requests[0]["request"])
        self.assertEqual(len(bridge.order), 4)


class HardBranch(unittest.TestCase):

    def test_duplicate_round_6_asks_one_high_effort_plan_before_generation(self):
        plan = json.dumps({"choice": "X1", "explanations": ["round 6 reproduced round 4's labels",
                                                            "the decoder rewrite changed no boundary group"],
                           "discriminating_prediction": "a grouping change moves bp_fe seeds by more than 4 points",
                           "falsifier": "all nine cells repeat round 2", "edit_brief": "exchange the dies of R2",
                           "expected_footprint": "structural",
                           "probe": {"kind": "decoder_change_vs_parent", "min_fraction": 0.0, "max_fraction": 0.2}})
        parent = ORIGINAL[1]["source"]
        bridge, _, log, _ = run_agent(ORIGINAL[:6], scripted(plan, combine(parent, EXCHANGE)),
                                      evaluate=echo(ORIGINAL[1]), limit=7, name="hard_branch")
        first, second = bridge.requests
        self.assertEqual((first["effort"], second["effort"]), ("high", "low"))
        self.assertTrue(first["system"].startswith("You plan one official experiment"))
        self.assertEqual(sorted(first["request"]["triggers"]), ["duplicate_outcome", "stalled_branch"])
        self.assertEqual([row["id"] for row in first["request"]["options"]], ["X1", "X2"])
        self.assertEqual(second["request"]["experiment_plan"]["edit_brief"], "exchange the dies of R2")
        submitted = events(log, "submitted")[-1]
        self.assertTrue(submitted["experiment"]["planned"])
        self.assertEqual(submitted["experiment"]["expect_footprint"], ["structural"])
        shape = next(row for row in submitted["preflight"]["static"] if row["check"] == "intervention_shape")
        self.assertEqual(shape["status"], "pass")


class DeclinedRepairs(unittest.TestCase):
    """Rounds 7 and 9: branching asks for targeted_repair; the gain it protects is inside the sensitivity."""

    def check(self, rounds):
        bridge, _, log, _ = run_agent(ORIGINAL[:rounds], scripted(combine(ORIGINAL[3]["source"], EXCHANGE)),
                                      evaluate=echo(ORIGINAL[3]), limit=rounds + 1, name="declined_repair_r%d" % rounds)
        self.assertEqual(len(bridge.requests), 1)  # no planning call: the decline rests on ledger facts
        request = bridge.requests[0]["request"]
        self.assertEqual((request["parent_id"], request["search_intent"]), (ORIGINAL[3]["candidate_id"], "decoder_only"))
        self.assertEqual(request["decision"]["reason"], "extend_best")
        self.assertIn("cell sensitivity", request["decision"]["note"])
        self.assertNotIn("repair_regression", request["decision"])  # the model is not asked to repair
        submitted = events(log, "submitted")[-1]
        self.assertEqual((submitted["parent_id"], submitted["policy_action"]), (ORIGINAL[3]["candidate_id"], "extend_best"))

    def test_round_7_repair_is_declined_end_to_end(self):
        self.check(7)

    def test_round_9_repair_is_declined_end_to_end(self):
        self.check(9)


class AgentErrorGuard(unittest.TestCase):

    def test_an_unexpected_error_returns_the_best_measured_candidate(self):
        def broken(agent):
            def fail(*args, **kwargs):
                raise RuntimeError("bridge reply could not be parsed")
            agent.submit_and_wait = fail
        _, returned, log, _ = run_agent(ORIGINAL[:4], scripted(), evaluate=echo(ORIGINAL[3]), limit=6, patch=broken)
        self.assertEqual(returned, ORIGINAL[3]["candidate_id"])
        self.assertEqual(events(log, "agent_error")[0]["error_type"], "RuntimeError")
        self.assertTrue(events(log, "selected"))


if __name__ == "__main__":
    unittest.main()
