"""Development replay tests. Archived data stays outside the staged Agent directory."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / "harness-exploration-feedback/next-harness/AgenticBench/agent/loss_decoder"
os.environ["AGENT_DIR"] = str(AGENT)
sys.path[:0] = [str(AGENT), str(ROOT / "harness-exploration/tests"), str(ROOT / "harness-ablation/tests")]
import test_loop
from cpu_checks import CPUChecks
from experiment_evidence import experiment_record
import stubs


class PayloadTest(unittest.TestCase):
    def test_synthetic_worker_overlaps_the_official_evaluation(self):
        entered, evaluating, overlapped = threading.Event(), threading.Event(), threading.Event()
        init = CPUChecks.__init__

        def setup(checks, files):
            init(checks, files)
            checks.available = True

        def check(checks, mode, *_):
            if mode == "ablation":
                entered.set()
                if evaluating.wait(4):
                    overlapped.set()
            return {"status": "ok"}

        def world(bridge, source, request_id):
            self.assertTrue(entered.wait(4))
            evaluating.set()
            return test_loop.gain()(bridge, source, request_id)

        with mock.patch.object(CPUChecks, "__init__", setup), mock.patch.object(CPUChecks, "run_check", check):
            _, _, _, error, _ = test_loop.run(world, evaluation_limit=1)
        self.assertIsNone(error)
        self.assertTrue(overlapped.is_set())

    def test_model_receives_same_record_on_generation_and_short_retry(self):
        bridge, _, _, error, _ = test_loop.run(test_loop.gain(), ["valid", "incomplete", "valid"], evaluation_limit=2)
        self.assertIsNone(error)
        plan = bridge.plans()[1]["request"]["experiment_record"]
        for req in bridge.generations()[1:]:
            self.assertEqual(req["request"]["experiment_record"], plan)
        self.assertEqual(len(plan["history"]), 1)
        self.assertTrue(plan["history"][0]["plan_at_submission"])
        seeds = plan["history"][0]["seed_results"]
        self.assertEqual(seeds["columns"][:3], ["case", "seed", "status"])
        self.assertEqual([row[:2] for row in seeds["rows"]], [[c["case"], str(c["seed"])] for c in bridge.evaluation_cells])
        self.assertIn("contract", plan["synthetic_probes"][0])

    def test_contract_failure_reaches_codegen_without_consuming_an_evaluation(self):
        original = CPUChecks.run_check
        failed = set()

        def reject_once(checks, mode, request_id, control_id, control, candidate):
            if not failed:
                failed.add(request_id)
                return {"status": "invalid", "seed": 17, "issue": "nonfinite loss"}
            return original(checks, mode, request_id, control_id, control, candidate)

        with mock.patch.object(CPUChecks, "run_check", reject_once):
            bridge, _, _, error, _ = test_loop.run(test_loop.gain(), evaluation_limit=1)
        self.assertIsNone(error)
        self.assertEqual(len(bridge.order), 1)
        self.assertNotIn(bridge.order[0], failed)
        self.assertIn("nonfinite loss", bridge.generations()[1]["request"]["previous_generation_issue"])

    def test_34_point_receipt_replay_preserves_measured_values_and_unknowns(self):
        archive = ROOT / "exports/2026-11-19-claude-expert-audit/runs/15332-claude-original-34"
        if not (archive / "round-04/receipt.json").is_file():
            self.skipTest("optional local receipt archive")
        summaries = [json.loads((archive / ("round-%02d" % number) / "receipt.json").read_text(encoding="utf8"))[
            "logged_feedback"] for number in range(1, 5)]
        latest, parent = summaries[-1], summaries[1]
        schedule = [{"case": c["case"], "seed": c["seed"]} for c in reversed(latest["cells"])]
        record = experiment_record("initial", "parent", parent["candidate_id"], None, summaries, schedule, [])
        self.assertEqual(round(record["history"][-1]["score"], 2), 34.75)
        self.assertEqual(record["official_initial_program"], "initial")
        self.assertIn("-initial", record["diff_from_initial"])
        self.assertEqual(len(record["history"]), len(summaries))
        for trial, summary in zip(record["history"], summaries):
            lookup = {(c["case"], str(c["seed"])): c for c in summary["cells"]}
            table = trial["seed_results"]
            self.assertEqual(len(table["rows"]), len(schedule))
            for i, fields in enumerate(table["rows"]):
                row = dict(zip(table["columns"], fields))
                key = (row["case"], row["seed"])
                self.assertEqual(key, (schedule[i]["case"], str(schedule[i]["seed"])))
                measured = lookup[key]["metrics"]
                self.assertEqual(row["wns_ns"], round(measured["final_global_wns_setup_ns"], 7))
                self.assertEqual(row["tns_ns"], round(measured["final_global_tns_setup_ns"], 7))
                self.assertEqual(row.get("raw_cut"), measured.get("tp_gnn_raw_cut_net_count"))
                if summary == latest and key == ("bp-ng45", "1002"):
                    self.assertAlmostEqual(row["delta_score_parent"], -19.5115299, places=6)
                    self.assertAlmostEqual(row["delta_tns_ns_parent"], -2171.8424864, places=6)
        self.assertTrue(all(v is None for v in record["start_measurements"]["rows"][0][3:]))

    def test_missing_failed_and_zero_are_distinct_on_each_seed(self):
        cells = [{"case": "design", "seed": i} for i in (1, 2, 3)]
        ok = {**cells[0], "status": "succeeded", "valid": True, "score": 0.0,
              "metrics": {"final_global_tns_setup_ns": 0.0}}
        failed = {**cells[1], "status": "failed", "valid": False, "score": -100,
                  "failure": {"stage": "20_partition", "reason": "invalid labels"}}
        trial = {"candidate_id": "child", "status": "failed", "case_scores": {}, "cells": [failed, ok]}
        table = experiment_record("a", "b", "parent", None, [trial], cells, [])["history"][0]["seed_results"]
        ok, failed, missing = [dict(zip(table["columns"], r)) for r in table["rows"]]
        self.assertEqual((ok["status"], ok["tns_ns"]), ("succeeded", 0))
        self.assertIsNone(ok["delta_score_parent"])
        self.assertEqual(failed["failure"]["stage"], "20_partition")
        self.assertIsNone(failed["tns_ns"])
        self.assertEqual((missing["seed"], missing["status"], missing["score"]), ("3", "missing", None))


class SeedDecisionTest(unittest.TestCase):
    def run_repair(self, last):
        rounds = [(20, -20, 0), (0, 0, 0), (0, 0, 0), last]

        def world(bridge, source, request_id):
            points = {("bp-ng45", str(seed)): change
                      for seed, change in zip((1001, 1002, 1003), rounds[len(bridge.order)])}
            return test_loop.gain(points)(bridge, source, request_id)

        bridge, _, events, error, _ = test_loop.run(world, evaluation_limit=4)
        self.assertIsNone(error)
        attempts = [e for e in events if e["event"] == "submitted"]
        verdict = [e for e in events if e["event"] == "evaluated"][-1]["ablation_result"]
        req = bridge.generations()[-1]["request"]
        parent = bridge.records[bridge.order[0]]["candidate_id"]
        self.assertEqual((attempts[-1]["parent_id"], req["parent_id"]), (parent, parent))
        decision = req["decision"]
        self.assertEqual(decision["reason"], "repair_within_case_seed_tradeoff")
        self.assertAlmostEqual(decision["seed_comparison"]["mean_delta"], 0)
        plan = decision["ablation"]
        self.assertEqual((plan["target"]["case"], plan["target"]["seed"]), ("bp-ng45", "1002"))
        self.assertEqual([c["seed"] for c in plan["protected_cells"]], ["1001"])
        return verdict

    def test_flat_case_changes_parent_selection_and_rewards_recovery(self):
        verdict = self.run_repair((20, -10, 0))
        self.assertEqual(verdict["status"], "passed")
        self.assertAlmostEqual(verdict["target_gain"], 10.0)

    def test_recovery_paid_for_by_neutral_seed_is_rejected_despite_higher_mean(self):
        verdict = self.run_repair((20, -8, -10))
        self.assertEqual(verdict["status"], "failed")
        self.assertGreater(verdict["score_delta"], 0)
        self.assertEqual([c["seed"] for c in verdict["other_seed_losses"]], ["1003"])

    def test_cross_design_tiny_incomplete_and_identical_labels(self):
        _, _, _, _, agent = test_loop.run(test_loop.gain(), evaluation_limit=0)
        result = {"source": "program", "candidate_id": "example"}
        def feedback(points):
            cells = [{"case": case, "seed": seed, "score_delta": delta} for case, seed, delta in points]
            return {"status": "succeeded", "parent_comparison": {"complete": True, "cells": cells}}

        for points in [[("a", "1", 20), ("b", "2", -20)], [("a", "1", 0.9), ("a", "2", -0.9)]]:
            self.assertFalse(agent.seed_tradeoffs(feedback(points)))
        trial = feedback([("a", "1", 20), ("a", "2", -20)])
        paired = trial["parent_comparison"]
        paired["complete"] = False
        self.assertFalse(agent.seed_tradeoffs(trial))
        paired["complete"] = True
        for cell in paired["cells"]:
            cell["assignment_vs_parent"] = {"changed_count": 0}
        self.assertTrue(agent.seed_tradeoffs(trial))
        self.assertIsNone(agent.seed_followup([result], [trial]))


class NativeProbeTest(unittest.TestCase):
    def test_real_cpu_worker_on_valid_and_invalid_candidates(self):
        with tempfile.TemporaryDirectory() as folder:
            checks = CPUChecks({"workspaces": folder, "framework": str(ROOT / "official/contest-source/AgenticBench")})
            if not checks.available:
                self.skipTest("needs CPU PyTorch/NumPy and the official Place-3D checkout")
            initial = (AGENT / "program.py").read_text(encoding="utf8")
            source = initial.replace("return -(", "return -1.25 * (").replace("return reference_global_two_way(",
                                                                              "return 1 - reference_global_two_way(")
            rid = "e-" + "1"*60
            self.assertEqual(checks.run_check("contract", rid, "initial", initial, source)["status"], "ok")
            self.assertEqual(checks.start(rid, "initial", initial, source), "started")
            checks.finish()
            result = checks.read(rid, "ablation")
            self.assertEqual(result["status"], "ok", result)
            self.assertEqual(len(result["rows"]), 8)
            for row in result["rows"]:
                if row["arm"] == "decoder_only":
                    self.assertEqual(row["raw_changed"], row["groups"])
                    self.assertEqual(row["raw_changed_up_to_flip"], 0)
            broken = initial.replace("return reference_global_two_way(", "return 2 + reference_global_two_way(")
            bad = checks.run_check("contract", "e-" + "2"*60, "initial", initial, broken)
            self.assertEqual((bad["status"], bad["arm"]), ("invalid", "candidate"))
            # A bad control invalidates this experiment, even if the candidate works.
            bad_control = checks.run_check("contract", "e-" + "3"*60, "control", broken, initial)
            self.assertEqual((bad_control["status"], bad_control["arm"]), ("inconclusive", "control"))
            bad_loss = stubs.variant(loss_body="    return positive_scores.sum() / (positive_scores.sum() - positive_scores.sum())")
            bad_gradient = checks.run_check("contract", "e-" + "4"*60, "initial", initial, bad_loss)
            self.assertEqual((bad_gradient["status"], bad_gradient["arm"]), ("invalid", "candidate"))

