"""Mocked-bridge runs of the search loop: reply repair, bridge errors, retry accounting, opening order.

    python3 -B -m unittest discover -s tests -v
    AGENT_DIR=original/next-harness/AgenticBench/agent/loss_decoder python3 -B -m unittest tests.test_loop -v
"""

import json
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness-ablation" / "tests"))
import stubs

DECODER = "def decode_tp_gnn_embeddings"
RESOURCE = {"status": "failed", "valid": False, "error_type": "ResourceAdmissionError",
            "reason": "insufficient available memory for candidate admission"}
CONTRACT = {"status": "failed", "valid": False, "score": -100.0, "error_type": "CandidateContractError",
            "reason": "20_partition: decoder must return one binary integer label per group"}


class Proposer:
    """Scripted model: a plan, then a new variant of whichever function the request allows to change."""

    def __init__(self, script=()):
        self.script, self.count = list(script), 0

    def __call__(self, bridge, system, request):
        if system.startswith("Return a short experiment plan"):
            return stubs.completed("Change one decision and check WNS and TNS.")
        if self.script:
            step = self.script.pop(0)
            if step == "incomplete":
                return stubs.INCOMPLETE
        self.count += 1
        loss, decoder = request["parent_program"].split(DECODER)
        decision = request.get("decision") or {}
        if request["search_intent"] == "decoder_only" or decision.get("component") == "decoder":
            decoder = ("(embeddings, node_areas, seed, max_iterations, balance_target):\n"
                       f'    """Variant {self.count}: exchange the dies of the reference grouping."""\n'
                       "    labels = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)\n"
                       f"    return {self.count} - labels * {self.count}\n# EVOLVE-BLOCK-END\n")
            if decision.get("opening_trial") == 3:
                decoder = decoder.replace(f"{self.count} - labels * {self.count}", "labels <= 0")
        else:
            loss = loss.split('    """')[0] + (
                f'    """Variant {self.count}: weight the negative pairs."""\n'
                "    return -(\n        F.logsigmoid(positive_scores).sum()\n"
                f"        + {1.0 + self.count / 10} * F.logsigmoid(-negative_scores).sum()\n"
                "    ) / max(1, source_batch_size)\n\n\n")
            if decision.get("opening_trial") == 3:
                loss = loss.split('    """')[0] + (
                    "    return F.logsigmoid(-negative_scores).mean() - F.logsigmoid(positive_scores).mean()\n\n\n"
                )
        return stubs.completed(loss + DECODER + decoder)


def gain(points=5.0, fraction=0.02):
    """Every cell gains the same number of points and moves a few percent of instances."""
    def evaluate(bridge, source, request_id):
        cells = stubs.cells_with(points)
        return {"candidate_id": "c-" + request_id[2:14], "status": "succeeded", "reason": None,
                "partition": stubs.broad_partition(fraction),
                "feedback": {"score": stubs.official_score(cells), "cells": cells}}
    return evaluate


def run(world, script=(), opening=None, evaluation_limit=3, before=None):
    folder = stubs.workdir()
    try:
        agent, copy = stubs.load_agent(folder, opening=opening)
        bridge = stubs.Bridge(folder, Proposer(script), evaluate=world, evaluation_limit=evaluation_limit)
        if before:
            before(bridge)
        error, returned = None, None
        try:
            returned = agent.Agent().run(bridge)
        except Exception as raised:  # the original Agent can crash; the tests report it as a failure
            error = raised
        events = [json.loads(line) for line in (copy / "search.jsonl").read_text().splitlines()]
        return bridge, returned, events, error, agent
    finally:
        shutil.rmtree(folder, ignore_errors=True)


class OpeningOrder(unittest.TestCase):
    def test_the_loss_control_goes_first_by_default(self):
        bridge, _, _, error, _ = run(gain(), evaluation_limit=1)
        self.assertIsNone(error)
        self.assertEqual(bridge.plans()[0]["request"]["search_intent"], "loss_only")

    def test_opening_uses_common_control_then_measures_exact_combination(self):
        def world(bridge, source, request_id):
            step = len(bridge.order)
            per_case = (
                {"bp_fe-ng45": 12.0, "ariane133-ng45": 18.0},
                {"bp-ng45": 20.0},
                {"bp_fe-ng45": 2.0},
                {"bp_fe-ng45": 12.0, "bp-ng45": 20.0, "ariane133-ng45": 18.0},
            )[step]
            points = {(c["case"], c["seed"]): per_case.get(c["case"], 0.0) for c in stubs.CELLS}
            return gain(points)(bridge, source, request_id)

        bridge, _result, events, error, agent = run(world, evaluation_limit=4)
        self.assertIsNone(error, error)
        attempts = [e for e in events if e["event"] == "submitted"]
        self.assertEqual([e.get("opening_trial") for e in attempts[:3]], [1, 2, 3])
        self.assertTrue(all(e["parent_id"] == bridge.baseline_candidate for e in attempts[:3]))
        self.assertEqual([set(e["changed_components"]) for e in attempts],
                         [{"loss"}, {"decoder"}, {"loss"}, {"decoder"}])
        control, donor, _, merged = [bridge.records[item] for item in bridge.order]
        self.assertEqual(attempts[3]["parent_id"], control["candidate_id"])
        self.assertEqual(attempts[3]["component_donor"], donor["candidate_id"])
        loss, decoder = agent.function_keys(merged["source"])
        self.assertEqual(loss, agent.function_keys(control["source"])[0])
        self.assertEqual(decoder, agent.function_keys(donor["source"])[1])
        self.assertEqual(len(bridge.generations()), 3)
        evaluated = [e for e in events if e["event"] == "evaluated"]
        self.assertEqual(evaluated[-1]["ablation_result"]["status"], "passed")

    def test_failed_combination_stays_out_of_final_selection_despite_higher_mean(self):
        def world(bridge, source, request_id):
            step = len(bridge.order)
            per_case = (
                {"bp_fe-ng45": 12.0, "ariane133-ng45": 18.0},
                {"bp-ng45": 22.0},
                {"bp_fe-ng45": 2.0},
                {"bp_fe-ng45": 0.0, "bp-ng45": 25.0, "ariane133-ng45": 18.0},
            )[step]
            points = {(cell["case"], cell["seed"]): per_case.get(cell["case"], 0.0) for cell in stubs.CELLS}
            return gain(points)(bridge, source, request_id)

        bridge, result, events, error, _ = run(world, evaluation_limit=4)
        self.assertIsNone(error, error)
        evaluated = [event for event in events if event["event"] == "evaluated"]
        self.assertEqual(evaluated[-1]["ablation_result"]["status"], "failed")
        self.assertGreater(evaluated[-1]["ablation_result"]["score_delta"], 0)
        self.assertNotEqual(result, bridge.records[bridge.order[-1]]["candidate_id"])

    def test_opening_without_complementary_donor_keeps_measured_parent(self):
        def world(bridge, source, request_id):
            step = len(bridge.order)
            return gain((18.0, -9.0, 0.0, 20.0)[step])(bridge, source, request_id)

        bridge, _, events, error, agent = run(world, evaluation_limit=4)
        self.assertIsNone(error, error)
        first = bridge.records[bridge.order[0]]
        fourth = bridge.records[bridge.order[3]]
        submitted = [event for event in events if event["event"] == "submitted"][-1]
        self.assertEqual(submitted["parent_id"], first["candidate_id"])
        self.assertEqual(submitted["decision"]["reason"], "continue_measured_opening")
        self.assertEqual(submitted["search_intent"], "decoder_only")
        self.assertEqual(agent.function_keys(first["source"])[0], agent.function_keys(fourth["source"])[0])

    def test_development_gate_checks_still_hold(self):
        # The synthetic gate checks of development/test_next_harness_replay.py, relative to the opening order.
        _, _, _, _, agent = run(gain(), evaluation_limit=0)
        winning = {"status": "succeeded", "candidate_id": "winning"}
        broad = {"parent_comparison": {"complete": True, "official_score_delta": 1,
                                       "cells": [{"case": x, "score_delta": 1} for x in ("a", "b", "c")]}}
        parent, intent, reason = agent.select_parent([winning], winning, [broad], None)
        self.assertEqual((parent, intent, reason["reason"]), (winning, agent.OPENING[0], "refine_supported_opening"))
        uncertain = {**broad, "timing_changes_with_identical_assignment": [{"case": "a"}]}
        parent, intent, reason = agent.select_parent([winning], winning, [uncertain], None)
        self.assertEqual((parent, intent, reason["reason"]),
                         (None, agent.OPENING[1], "test_alternative_component_after_opening"))


class OverlongReplies(unittest.TestCase):
    """Server 2 round 4: two replies used the whole output allowance and returned no text."""

    @classmethod
    def setUpClass(cls):
        cls.bridge, cls.returned, cls.events, cls.error, _ = run(
            gain(), script=["valid", "incomplete", "incomplete", "incomplete", "valid", "valid"])

    def test_three_overlong_replies_do_not_end_the_search(self):
        self.assertIsNone(self.error)
        self.assertEqual(len(self.bridge.order), 3, [event["event"] for event in self.events])

    def test_the_retry_after_an_overlong_reply_is_shorter(self):
        generations = self.bridge.generations()
        before, after = generations[1]["request"], generations[2]["request"]  # around the first incomplete reply
        self.assertIn("training_cells", before)
        self.assertNotIn("training_cells", after)
        self.assertIn("complete program only", after["previous_generation_issue"])

    def test_the_plan_is_rebuilt_after_three_rejections(self):
        self.assertIn("replan", [event["event"] for event in self.events])


class BridgeErrors(unittest.TestCase):
    def test_a_transient_status_error_does_not_crash_the_run(self):
        def world(bridge, source, request_id):
            if not bridge.order:
                bridge.faults["status"] = 2  # the next two status calls fail
            return gain()(bridge, source, request_id)

        bridge, returned, _, error, _ = run(world)
        self.assertIsNone(error, error)
        self.assertEqual(len(bridge.order), 3)

    def test_a_submit_error_with_no_bridge_record_is_not_fatal(self):
        bridge, returned, events, error, _ = run(gain(), before=lambda bridge: bridge.faults.update(submit=1))
        self.assertIsNone(error, error)
        self.assertEqual(len(bridge.order), 3)
        self.assertIn("submit_failed", [event["event"] for event in events])


class RetryAccounting(unittest.TestCase):
    def test_an_infrastructure_failure_is_resubmitted_once_without_a_model_call(self):
        def world(bridge, source, request_id):
            reply = gain()(bridge, source, request_id)
            if not bridge.order:  # the first submission loses one cell to resource admission
                reply["feedback"]["cells"][4] = {**reply["feedback"]["cells"][4], **RESOURCE}
                reply["feedback"]["cells"][4].pop("score")
                reply["status"] = "failed"
            return reply

        bridge, returned, events, error, _ = run(world)
        self.assertIsNone(error, error)
        first, second = (bridge.records[request_id] for request_id in bridge.order[:2])
        self.assertTrue(second["request_id"].startswith("r-"), bridge.order)
        self.assertEqual(first["source"], second["source"])
        between = [event for event in events if event["event"] == "model_request"]
        self.assertEqual(len(between), 2 + 2, "one plan and one generation per new candidate only")

    def test_a_contract_failure_is_repaired_in_the_candidate_that_broke_it(self):
        def world(bridge, source, request_id):
            reply = gain()(bridge, source, request_id)
            if not bridge.order:
                reply["feedback"]["cells"] = [{**cell, **CONTRACT} for cell in reply["feedback"]["cells"]]
                reply["status"] = "failed"
            return reply

        bridge, _, _, error, _ = run(world, opening="decoder_only", evaluation_limit=2)
        self.assertIsNone(error, error)
        failed = bridge.records[bridge.order[0]]
        request = bridge.plans()[1]["request"]
        self.assertEqual((request["search_intent"], request["parent_id"]), ("repair", failed["candidate_id"]))


if __name__ == "__main__":
    unittest.main()
