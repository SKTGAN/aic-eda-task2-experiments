"""Check the opening and repair decisions with recorded and controlled receipts."""

from pathlib import Path
import shutil
import unittest

import stubs
from test_three_servers import ORIGINAL, PANEL, PANEL_CELLS, replay


class AblationReplay(unittest.TestCase):
    def test_weak_opening_loss_gets_one_controlled_trial_before_decoder_switch(self):
        request, _, _ = replay(PANEL[:1], "loss_only", cells=PANEL_CELLS, limit=3)
        self.assertEqual(request["parent_id"], PANEL[0]["candidate_id"])
        self.assertEqual(request["search_intent"], "repair")
        decision = request["decision"]
        self.assertEqual(decision["reason"], "test_opening_loss")
        self.assertEqual(decision["component"], "loss")
        self.assertEqual(decision["ablation"]["target"]["case"], "ariane133-ng45")

    def test_repair_keeps_original_round_7_gains_in_its_control(self):
        request, _, _ = replay(ORIGINAL[:7], "decoder_only")
        self.assertEqual(request["parent_id"], ORIGINAL[6]["candidate_id"])
        decision = request["decision"]
        self.assertEqual(decision["reason"], "repair_tradeoff")
        self.assertEqual(decision["component"], "loss")
        plan = decision["ablation"]
        self.assertEqual((plan["target"]["case"], plan["target"]["seed"]), ("ariane133-ng45", "1001"))
        self.assertIn(("ariane133-ng45", "1002"), {(x["case"], x["seed"]) for x in plan["protected_cells"]})

    def test_tradeoff_is_rejected_even_when_total_score_improves(self):
        folder = stubs.workdir()
        try:
            agent, _ = stubs.load_agent(Path(folder))
            plan = {
                "target": {"case": "weak", "seed": "1"},
                "protected_cells": [{"case": "strong", "seed": "1"}],
                "minimum_target_gain": 2,
                "maximum_protected_loss": 2,
                "maximum_case_mean_loss": 2,
            }
            paired = {
                "complete": True, "parent_source": "run_evaluation", "official_score_delta": 5,
                "cells": [{"case": "weak", "seed": "1", "score_delta": 12},
                          {"case": "strong", "seed": "1", "score_delta": 0}],
            }
            self.assertEqual(agent.assess_ablation(plan, paired)["status"], "passed")
            paired["cells"][1]["score_delta"] = -4
            result = agent.assess_ablation(plan, paired)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["protected_losses"][0]["case"], "strong")
            control = {"candidate_id": "control", "request_id": "first", "status": "succeeded"}
            trial = {"candidate_id": "trial", "request_id": "second", "status": "succeeded"}
            observed = {"attempt": {"parent_id": "control", "changed_components": {"loss": "one change"},
                                    "ablation": plan}, "ablation_result": result}
            parent, intent, decision = agent.select_parent([control, trial], trial, [{}, observed], None)
            self.assertEqual((parent, intent, decision["reason"]),
                             (control, "decoder_only", "keep_measured_ablation_control"))
            paired["complete"] = False
            self.assertEqual(agent.assess_ablation(plan, paired)["status"], "unverified")
        finally:
            shutil.rmtree(folder, ignore_errors=True)
