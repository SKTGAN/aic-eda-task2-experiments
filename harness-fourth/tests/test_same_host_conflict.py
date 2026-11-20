from pathlib import Path
import tempfile
import unittest

import stubs


class SameHostStart(unittest.TestCase):
    def test_conflicting_repeat_is_excluded_even_when_scores_tie(self):
        with tempfile.TemporaryDirectory() as temp:
            agent, _ = stubs.load_agent(Path(temp))

        def cell(seed, score, wns):
            return {"case": "bp-ng45", "seed": seed, "status": "succeeded", "score": score,
                    "metrics": {"final_global_wns_setup_ns": wns}}

        def receipt(rid, *cells):
            return {"request_id": rid, "status": "succeeded", "feedback": {"cells": cells}}

        origin = {"feedback": {"score": 15, "cells": [cell("1001", 10, -1), cell("1002", 20, -2)]}}
        history = [receipt("e-1", cell("1001", -100, -3), cell("1002", 8, -1)),
                   receipt("e-2", cell("1001", -100, -4)), receipt("e-3", cell("1001", -100, -3))]
        matches = {row["request_id"]: {("bp-ng45", c["seed"]): {"partition_assignment_changed_count": 0}
                                      for c in row["feedback"]["cells"]} for row in history}
        start = agent.same_host_start(origin, history, matches)
        self.assertEqual([c["score"] for c in start["feedback"]["cells"]], [10, 8])
        self.assertEqual(start["summary"]["score_kind"], "mixed_reference")
        self.assertEqual(start["summary"]["conflicting_cells_using_published"], [["bp-ng45", "1001"]])
