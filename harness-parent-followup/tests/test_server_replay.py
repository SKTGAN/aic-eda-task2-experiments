"""Replay both servers' completed official receipts through the Agent and check its next decision.

Each test restarts the Agent after the first k rounds of a real run (same receipts, organizer partition
diagnostics and lineage as recorded on the server, same opening order) and records the plan request it
builds for round k+1. No model call or physical job is made.

    python3 -B -m unittest discover -s tests -v
    AGENT_DIR=original/next-harness/AgenticBench/agent/loss_decoder python3 -B -m unittest tests.test_server_replay -v
"""

import json
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stubs

RECEIPTS = json.loads((Path(__file__).resolve().parent / "fixtures" / "server_receipts.json").read_text())
SERVER_1, SERVER_2 = RECEIPTS["server-1-claude"], RECEIPTS["server-2-local-harness"]


def next_decision(rounds):
    """The plan request the Agent builds after the given rounds, and the start reference it used."""
    folder = stubs.workdir()
    try:
        events = [{"event": "submitted", "request_id": row["request_id"], "decision": row["decision"],
                   **row["attempt"]} for row in rounds]
        agent, _ = stubs.load_agent(folder, opening="decoder_only", log_events=events)  # the order both servers ran
        receipts = [{"request_id": row["request_id"], "candidate_id": row["candidate_id"], "status": row["status"],
                     "source": row["source"], "reason": None, "partition": row["partition"],
                     "feedback": {"score": row["score"], "cells": row["cells"]}} for row in rounds]
        bridge = stubs.Bridge(folder, lambda bridge, system, request: stubs.completed("Plan."),
                              receipts=receipts, model_limit=1)
        bridge.baseline_candidate = rounds[0]["attempt"]["parent_id"]
        returned = agent.Agent().run(bridge)
        request = bridge.requests[0]["request"]
        return request, returned
    finally:
        shutil.rmtree(folder, ignore_errors=True)


class OpeningDecoderControls(unittest.TestCase):
    """Both decoder openings kept the start grouping on 8 of 9 cells, exchanging the dies on several."""

    def test_server_1_round_1_is_orientation_only(self):
        request, _ = next_decision(SERVER_1[:1])
        self.assertEqual(request["search_intent"], "loss_only")
        self.assertEqual((request["decision"].get("evidence") or {}).get("reason"), "orientation_only",
                         request["decision"])

    def test_server_2_round_1_is_orientation_only_and_measures_the_host(self):
        request, _ = next_decision(SERVER_2[:1])
        self.assertEqual((request["decision"].get("evidence") or {}).get("reason"), "orientation_only",
                         request["decision"])
        self.assertEqual(request.get("start_reference", {}).get("same_host_cells"), 5, request.get("start_reference"))


class Server2Round3(unittest.TestCase):
    """After rounds 1-2 the harness judged its best candidate against a start this host never reaches."""

    @classmethod
    def setUpClass(cls):
        cls.request, cls.returned = next_decision(SERVER_2[:2])

    def test_start_reference_uses_the_five_cells_measured_on_this_host(self):
        start = self.request.get("start_reference") or {}
        self.assertEqual(start.get("same_host_cells"), 5, start)
        self.assertAlmostEqual(start.get("same_host_score", 0), 3.95, delta=0.01)

    def test_round_2_is_a_narrow_gain_not_a_broad_regression(self):
        trial = self.request["prior_trials"][-1]
        self.assertEqual(trial["evidence"]["reason"], "narrow_gain")
        self.assertEqual(self.request["decision"]["reason"], "follow_up_case_champion")
        self.assertEqual(self.request["parent_id"], trial["candidate_id"])

    def test_best_candidate_is_still_returned(self):
        self.assertEqual(self.returned, SERVER_2[1]["candidate_id"])


class Server1Round5(unittest.TestCase):
    """Round 4 beat round 2 by 5.33 points; ariane133-ng45/1001 alone (a die exchange) carries 5.31."""

    @classmethod
    def setUpClass(cls):
        cls.request, cls.returned = next_decision(SERVER_1[:4])

    def test_round_4_gain_is_narrow_and_named(self):
        decision = self.request["decision"]
        self.assertEqual(decision["reason"], "narrow_gain", decision)
        self.assertEqual((decision["largest_cell"]["case"], decision["largest_cell"]["seed"]),
                         ("ariane133-ng45", "1001"))
        self.assertGreater(decision["largest_cell_share"], 0.95)

    def test_next_hypothesis_builds_on_round_2_not_on_the_die_exchange(self):
        self.assertEqual(self.request["parent_id"], SERVER_1[1]["candidate_id"])
        self.assertEqual(self.request["search_intent"], "diversify")

    def test_final_answer_is_still_the_best_official_score(self):
        self.assertEqual(self.returned, SERVER_1[3]["candidate_id"])


class UnchangedDecisions(unittest.TestCase):
    """Cases where the original harness already decided well must not change."""

    def test_server_1_refines_round_2(self):
        request, _ = next_decision(SERVER_1[:2])
        self.assertEqual((request["search_intent"], request["parent_id"]), ("refine", SERVER_1[1]["candidate_id"]))

    def test_server_1_explores_from_round_2_after_the_refinement_lost(self):
        request, _ = next_decision(SERVER_1[:3])
        self.assertEqual(request["parent_id"], SERVER_1[1]["candidate_id"])
        self.assertEqual(request["search_intent"], "diversify")

    def test_server_2_round_3_kept_the_start_grouping(self):
        request, _ = next_decision(SERVER_2[:3])
        self.assertEqual(request["prior_trials"][-1]["evidence"]["reason"], "partition_mostly_unchanged")
        self.assertEqual(request["decision"]["reason"], "follow_up_case_champion")
        self.assertEqual(request["parent_id"], SERVER_2[1]["candidate_id"])
        self.assertEqual(request["search_intent"], "decoder_only")


if __name__ == "__main__":
    unittest.main()
