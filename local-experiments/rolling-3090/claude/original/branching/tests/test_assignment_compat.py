import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class AssignmentCompatibilityTest(unittest.TestCase):
    def test_global_flip_is_retained_after_matching_instance_names(self):
        agent = Path(__file__).resolve().parents[1] / "AgenticBench/agent/loss_decoder"
        with patch.object(sys, "path", [str(agent)] + sys.path), tempfile.TemporaryDirectory() as tmp:
            from paired_feedback import ASSIGNMENT_PATHS, _assignment_difference

            root = Path(tmp).resolve()
            cell = ("demo", "1001")
            def receipt(request, indices, flip):
                output = root / request
                target = output / "cells/demo/1001/result" / ASSIGNMENT_PATHS[0]
                target.parent.mkdir(parents=True)
                with target.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(["inst_name", "die"])
                    for index in indices:
                        writer.writerow(["n" + str(index), ("bottom", "top")[(index % 2) ^ flip]])
                return {"request_id": request, "artifacts_dir": str(output), "status": "succeeded"}
            parent = receipt("parent", range(257), 0)
            child = receipt("child", reversed(range(257)), 1)
            diff = _assignment_difference(cell, parent, child, str(root), {}, {})
            self.assertEqual(diff["changed_count"], 257)
            self.assertEqual(diff["flip_adjusted_changed_count"], 0)
            self.assertFalse(diff["identical"])
