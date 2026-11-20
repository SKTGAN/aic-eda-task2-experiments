from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "AgenticBench/agent/loss_decoder"))
from decision_evidence import decision_evidence, timing_twins


def fixture(candidate):
    return {"request_id": "r-" + candidate, "candidate_id": candidate, "status": "succeeded",
            "score": -100.0, "attempt": {"parent_id": "start", "changed_components": {"loss": "sample"}},
            "cells": [{"case": case, "seed": seed, "score": -100.0, "status": "succeeded", "valid": True,
                       "metrics": {"final_global_wns_setup_ns": -3.5, "final_global_tns_setup_ns": -600.0}}
                      for case in ("a", "b", "c") for seed in (1, 2, 3)]}


class TrainingEvidenceTests(unittest.TestCase):
    def test_score_floor_does_not_mask_physical_difference(self):
        left, right = fixture("old"), fixture("new")
        right["cells"].reverse()
        self.assertTrue(timing_twins(left, right, left["cells"]))
        right["cells"][0]["metrics"]["final_global_tns_setup_ns"] -= 1
        self.assertFalse(timing_twins(left, right))

    def test_unavailable_and_penalized_cannot_form_twins(self):
        good = fixture("one")
        for field, value in (("status", "penalized"), ("valid", False), ("case", "bogus"),
                             ("failure", {"kind": "runtime_environment"}), ("metrics", {})):
            with self.subTest(field=field):
                other = fixture("two")
                other["cells"][0][field] = value
                self.assertFalse(timing_twins(good, other))
        duplicate = fixture("bad")
        duplicate["cells"][0] = duplicate["cells"][1]
        self.assertFalse(timing_twins(duplicate, duplicate))
        self.assertFalse(timing_twins(good, good, duplicate["cells"]))

    def test_history_finds_older_twin_with_changed_assignment(self):
        first, later, latest = map(fixture, ("first", "later", "latest"))
        later["cells"][0]["metrics"]["final_global_wns_setup_ns"] -= 1
        rows = [{"case": row["case"], "seed": row["seed"], "score_delta": 0} for row in latest["cells"]]
        rows[0].update(score_delta=-45, score_delta_terms={"wns_points": -1, "tns_points": -50,
                                                          "score_floor_delta_points": 6})
        rows[1].update(score_delta=9, assignment={"source": "published_aligned_assignments",
                                                  "identical": False, "flip_adjusted_changed_fraction": 0})
        latest["parent_comparison"] = {"complete": True, "cells": rows}
        evidence = decision_evidence(latest, [first, later, latest, fixture("future")])
        self.assertEqual(evidence["related_prior_trial"]["candidate_id"], "first")
        self.assertEqual(evidence["timing_twin_count"], 1)
        paired = evidence["parent_effect"]
        self.assertEqual((paired["gains_in_matrix_points"], paired["losses_in_matrix_points"]), (1, -5))
        self.assertEqual(paired["worst_loss"]["points"]["score_floor_delta_points"], 6)
        self.assertEqual(paired["worst_loss"]["seed"], 1)
        self.assertFalse(paired["all_nine_assignments_verified_identical"])
        self.assertEqual(paired["all_labels_flipped_cells"], 1)


if __name__ == "__main__":
    unittest.main()
