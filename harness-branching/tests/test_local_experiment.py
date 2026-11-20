import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


HARNESS = Path(__file__).resolve().parents[1]
ROOT = HARNESS.parent / "official" / "contest-source"
AGENT = HARNESS / "AgenticBench" / "agent" / "loss_decoder"


@unittest.skipUnless(importlib.util.find_spec("torch") and importlib.util.find_spec("numpy"),
                     "paired numerical experiment requires PyTorch and NumPy")
class LocalExperimentTest(unittest.TestCase):
    def test_paired_gradients_and_runtime_errors(self):
        with patch.object(sys, "path", [str(AGENT), str(ROOT / "Place-3D"), *sys.path]):
            from local_experiment import measure
            parent = (AGENT / "program.py").read_text(encoding="utf-8")
            declared = parent.replace("objective.", "objective. Probe: halve_feature[6] -> incident_score_grad_norm down")
            child = declared.replace("return -(", "return (node_features[graph_sources, 6] * graph_scores).mean() - (")
            result = measure(dict(parent=parent, candidate=child, components=["loss", "decoder"]))
            self.assertEqual(result["status"], "supported_on_fixture")
            self.assertEqual(result["parent"]["base"], result["parent"]["perturbed"])
            self.assertGreater(result["paired_difference"]["base"]["max_abs_embedding_grad_delta"], 0)
            self.assertEqual(result["paired_difference"]["changed_labels"], 0)
            for role in ("parent", "candidate"):
                self.assertEqual(set(result[role]["labels"]), {0, 1})
            full = result["candidate"]["base"]["incident_score_grad_norm"]
            half = result["candidate"]["perturbed"]["incident_score_grad_norm"]
            self.assertGreater(full, 0)
            self.assertAlmostEqual(half, full / 2)
            inert = measure(dict(parent=parent, candidate=declared, components=["loss"]))
            self.assertEqual(inert["status"], "claim_mismatch")
            self.assertEqual(inert["observed_direction"], "unchanged")
            self.assertEqual(inert["paired_difference"]["base"]["max_abs_embedding_grad_delta"], 0)
            broken = parent.replace("return -(", "return graph_scores.mean() / 0 + (")
            self.assertEqual(measure(dict(parent=parent, candidate=broken, components=["loss"]))["status"],
                             "candidate_error")
            self.assertEqual(measure(dict(parent=broken, candidate=parent, components=["loss"]))["status"],
                             "unavailable")
