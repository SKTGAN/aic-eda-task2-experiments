from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "AgenticBench/agent/loss_decoder"))
from search_control import select_next


class TwoRoundSearch(unittest.TestCase):
    def second(self, deltas, fractions, valid=True):
        cells = [{"case": "example", "seed": str(i), "score": d, "valid": valid,
                  "status": "succeeded", "partition_change_vs_initial":
                  {"partition_assignment_changed_fraction": f}}
                 for i, (d, f) in enumerate(zip(deltas, fractions))]
        pairs = [{"case": c["case"], "seed": c["seed"], "score_delta": c["score"],
                  "tns_slack_delta_ns": c["score"]} for c in cells]
        first = {"candidate_id": "first", "score": sum(deltas) / len(cells), "status": "succeeded",
                 "cells": cells, "attempt": {"parent_id": "start", "changed_components": {"loss": "edit"}},
                 "parent_comparison": {"complete": True, "cells": pairs}}
        return select_next([first], "start", "", cells, opening=("loss_only", "decoder_only"))

    def test_repeated_measured_gain_uses_actual_parent(self):
        parent, intent, evidence = self.second([4, 2, -1], [.01, .02, .0])
        self.assertEqual((parent, intent), ("first", "decoder_only"))
        self.assertEqual(evidence["protect_case_seeds"], {"example": ["0", "1"]})

    def test_inert_loss_gets_a_second_loss_attempt(self):
        self.assertEqual(self.second([2, 4, 6], [0, 1, 0])[:2], ("first", "loss_only"))

    def test_one_seed_cannot_establish_repeatable_gain(self):
        self.assertEqual(self.second([7, -1, -1], [.01, .02, .04])[:2], ("start", "loss_only"))

    def test_missing_assignments_and_failures_are_not_local_evidence(self):
        self.assertEqual(self.second([1, 2, 3], [None] * 3)[0], "start")
        self.assertEqual(self.second([1, 2, 3], [.1] * 3, valid=False)[0], "start")


if __name__ == "__main__":
    unittest.main()
