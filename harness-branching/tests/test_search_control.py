import copy
from pathlib import Path
from statistics import mean
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "AgenticBench/agent/loss_decoder"))
from search_control import select_next


SCHEDULE = [{"case": case, "seed": seed} for case in ("a", "b", "c") for seed in ("1", "2", "3")]


def trial(name, parent, scores, component="loss", action=None):
    cells = [{**cell, "status": "succeeded", "valid": True, "score": score,
              "metrics": {"final_global_wns_setup_ns": score, "final_global_tns_setup_ns": -100 + score}}
             for cell, score in zip(SCHEDULE, scores)]
    return {"candidate_id": name, "status": "succeeded", "score": mean(scores), "cells": cells,
            "attempt": {"parent_id": parent, "changed_components": {component: {}}, "policy_action": action},
            "parent_comparison": {"parent_id": parent, "complete": len(cells) == len(SCHEDULE)}}


def plan(*rows):
    return select_next(rows, "start", "", SCHEDULE)


class SearchControlTest(unittest.TestCase):
    def setUp(self):
        self.base = trial("best", "start", [15] * 9, component="decoder")
        self.alt = trial("other", "start", [11] * 9)

    def test_tied_official_scores_alone_do_not_prove_repeated_timing(self):
        changed = trial("new", "best", [15] * 9)
        changed["cells"][2]["metrics"]["final_global_tns_setup_ns"] -= 1
        parent, scope, decision = plan(self.base, self.alt, changed)
        self.assertEqual((parent, scope, decision["reason"]), ("best", "decoder_only", "extend_best"))
        changed["cells"][2]["metrics"]["final_global_tns_setup_ns"] += 1
        parent, scope, decision = plan(self.base, self.alt, changed)
        self.assertEqual((parent, decision["reason"], decision["trigger"]),
                         ("other", "switch_branch", "same_measured_timing"))
        self.assertNotEqual(parent, "new")

    def test_budget_is_per_parent_and_partial_matrix_cannot_become_the_best(self):
        weak1 = trial("w1", "best", [10] * 9)
        partial = trial("partial", "other", [80] * 8)
        weak2 = trial("w2", "best", [8] * 9)
        self.assertEqual(plan(self.base, self.alt, weak1, partial, weak2)[2]["reason"], "extend_best")
        decision = plan(self.base, self.alt, partial, weak1, weak2)
        self.assertEqual((decision[0], decision[2]["trigger"]), ("other", "two_unsuccessful_children"))
        weak2["cells"][1] = copy.deepcopy(weak2["cells"][2])
        self.assertEqual(plan(self.base, self.alt, weak1, weak2)[2]["reason"], "extend_best")

    def test_concentrated_loss_has_one_repair_then_returns_to_best(self):
        risky = trial("risky", "best", [-65, 21, 21, 24, 23, 15, 13, 12, 12])
        parent, scope, decision = plan(self.base, self.alt, risky)
        self.assertEqual((parent, scope, decision["reason"]), ("risky", "loss_only", "targeted_repair"))
        self.assertEqual(decision["repair_regression"]["case"], "a")
        self.assertEqual(decision["incumbent_id"], "best")
        repair = trial("repair", "risky", [-95, 24, 25, 25, 24, 15, 10, 10, 10], action="targeted_repair")
        self.assertEqual(plan(self.base, self.alt, risky, repair)[0], "best")
        risky["parent_comparison"]["parent_id"] = "other"
        self.assertEqual(plan(self.base, self.alt, risky)[2]["reason"], "extend_best")
        only_one_case = trial("one_case", "best", [20, 25, 24, -80, 15, 15, 15, 15, 15])
        self.assertEqual(plan(self.base, self.alt, only_one_case)[2]["reason"], "extend_best")

    def test_infrastructure_loss_is_not_an_algorithmic_observation(self):
        offline = trial("offline", "best", [-100] * 9)
        offline["cells"][0].update(valid=False, status="failed", failure={"kind": "runtime_environment"})
        decision = plan(self.base, self.alt, offline)
        self.assertEqual((decision[0], decision[2]["reason"]), ("best", "execution_evidence_unusable"))
        offline["cells"][0]["failure"] = {"kind": "candidate_contract", "component": "decoder"}
        parent, scope, action = plan(self.base, self.alt, offline)
        self.assertEqual((parent, scope, action["reason"]), ("best", "decoder_only", "replace_invalid_component"))


if __name__ == "__main__":
    unittest.main()
