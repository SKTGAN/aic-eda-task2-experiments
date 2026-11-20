"""Offline integration of the opening policy, official parser and bridge client."""

import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
from statistics import mean
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


HARNESS = Path(__file__).resolve().parents[1]
OFFICIAL = HARNESS.parent / "official" / "contest-source" / "AgenticBench"
AGENT_FILES = HARNESS / "AgenticBench" / "agent" / "loss_decoder"
WORST = ("bp-ng45", "1002")


def edited(source, component, mechanism, decision, prediction, falsifier, before, after):
    original = next(ast.get_docstring(f) for f in ast.parse(source).body
                    if ("loss" in f.name) == (component == "loss"))
    docstring = (f"Mechanism: {mechanism}; Decision: {decision}; "
                 f"Prediction: {prediction}; Falsifier: {falsifier}")
    return source.replace(original, docstring, 1).replace(before, after, 1)


def load_case(folder):
    # The validator only needs program_safety. Skip local_bench's eager EDA imports
    # so the test uses its real source without requiring the GPU evaluator or PyYAML.
    namespace = types.ModuleType("local_bench")
    namespace.__path__ = [str(OFFICIAL / "local_bench")]
    sys.modules.setdefault("local_bench", namespace)
    spec = importlib.util.spec_from_file_location("test_harness_agent", folder / "agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecondCandidateTest(unittest.TestCase):
    def test_first_receipt_guides_next_opening_and_official_total_drives_branch(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules), patch.object(sys, "path", list(sys.path)):
            folder = Path(tmp) / "agent"
            shutil.copytree(AGENT_FILES, folder, ignore=shutil.ignore_patterns("__pycache__", "search.jsonl"))
            (folder / "opening.txt").write_text("decoder_only\n", encoding="utf-8")
            sys.path[:0] = [str(folder), str(OFFICIAL)]
            harness = load_case(folder)
            from contest2.agent_api import AgentContext
            from contest2.scoring import PUBLIC_SPLITS, SEEDS, reference_table, score_metrics
            from local_tasks.tp_gnn_local_task_definitions import DECODER_TASK, validate_program

            initial = validate_program((OFFICIAL / "local_tasks" / DECODER_TASK / "initial_program.py")
                                       .read_text(encoding="utf-8"), DECODER_TASK)
            baseline_id = "synthetic-official-initial"
            starter = "reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)"
            decoder_a = edited(initial, "decoder", "Swap labels from the reference assignment",
                               "exchanges upper and lower tiers", "WNS changes with vertical orientation",
                               "paired WNS stays flat", starter, "1 - " + starter)
            decoder_b = edited(initial, "decoder", "Threshold the first coordinate at its mean",
                               "assigns a tier from one coordinate", "nonempty partitions change TNS",
                               "paired TNS does not improve", starter,
                               "(embeddings[:, 0] >= np.mean(embeddings[:, 0])).astype(np.int64)")
            loss_before = "F.logsigmoid(-negative_scores).sum()"
            loss_a = edited(initial, "loss", "Reweight sampled negative pairs",
                            "changes embedding separation before decoding", "paired TNS improves",
                            "TNS regresses consistently", loss_before, "0.8 * " + loss_before)
            loss_b = edited(initial, "loss", "Regularize embedding magnitude",
                            "changes learned coordinates before decoding", "paired WNS improves",
                            "paired WNS remains unchanged", ") / max(1, source_batch_size)",
                            ") / max(1, source_batch_size) + 0.01 * embeddings.square().mean()")
            decoder_boundary = "\n\ndef decode_tp_gnn_embeddings"
            followup = decoder_boundary.join((loss_a.split(decoder_boundary)[0],
                                              decoder_b.split(decoder_boundary)[1]))
            by_opening = {"decoder_only": (decoder_a, decoder_b), "loss_only": (loss_a, loss_b)}
            cells = [{"case": case, "seed": str(seed)} for case in PUBLIC_SPLITS["train"] for seed in SEEDS]
            cases = reference_table()["cases"]
            evaluations = Path(tmp) / "evaluations"

            class Bridge(AgentContext):
                def __init__(self):
                    self.submitted = []
                    self.model_inputs = []
                    self.receipts = {}
                    super().__init__(socket_path="synthetic")

                def _call(self, method, params):
                    if method == "initial":
                        return {"task": "loss_decoder", "baseline_candidate": baseline_id,
                                "evaluation_cells": cells, "files": {"framework": str(OFFICIAL),
                                "workspaces": tmp, "evaluations": str(evaluations)}}
                    if method == "status":
                        remaining = 3 - len(self.submitted)
                        return {"history": [{"request_id": rid} for rid in self.receipts],
                                "evaluation_dispatch_allowed": remaining > 0,
                                "model_dispatch_allowed": remaining > 0,
                                "evaluations_remaining": remaining, "model_stop_reasons": []}
                    if method == "evaluation_status":
                        return deepcopy(self.receipts[params["request_id"]])
                    if method == "model_responses_create":
                        return self.respond(params["payload"])
                    if method == "submit_evaluation":
                        self.submit(params)
                        return {"status": "accepted", "request_id": params["request_id"]}
                    raise AssertionError(f"Unexpected bridge call {method}")

                def respond(self, payload):
                    request = json.loads(payload["input"][-1]["content"])
                    count = len(self.submitted)
                    self.model_inputs.append((count, request))
                    if len(self.model_inputs) > 7:
                        raise AssertionError("Unexpected retry in the three-evaluation scenario")
                    if count == 2:
                        source = followup
                    elif "proposals" in request:
                        source = "PICK B: The alternative changes the assignment mechanism."
                    else:
                        source = by_opening[request["search_intent"]]["proposal_a" in request]
                    return {"status": "completed", "output": [{"type": "message", "content": [
                        {"type": "output_text", "text": source}]}]}

                def submit(self, params):
                    rid = params["request_id"]
                    source = validate_program(params["source"], DECODER_TASK)
                    index = len(self.submitted)
                    self.submitted.append((rid, source))
                    rows = []
                    for cell in cells:
                        case, seed = cell["case"], cell["seed"]
                        baseline = cases[case]["measurements"]["loss_decoder"][seed]
                        wns_scale, tns_scale = ((0.55, 0.52), (1.29, 1.38), (0.96, 0.98))[index]
                        if index == 0 and (case, seed) == WORST:
                            tns_scale = 2.5
                        metrics = score_metrics(case, {"runs_successfully": 1, "sta_graph_complete": 1,
                            "timing_evaluation_boundary": "post-opt-pre-cts",
                            "combined_score": (0, 80, 95)[index],
                            "final_global_wns_setup_ns": baseline["wns_ns"] * wns_scale,
                            "final_global_tns_setup_ns": baseline["tns_ns"] * tns_scale})
                        rows.append({**cell, "score": metrics["combined_score"], "raw_score": metrics["raw_score"],
                                     "valid": True, "status": "succeeded", "metrics": metrics})
                    self.receipts[rid] = {"request_id": rid, "candidate_id": f"accepted-{index + 1}",
                                         "status": "succeeded", "source": source,
                                         "feedback": {"score": mean(row["score"] for row in rows), "cells": rows}}

            bridge = Bridge()
            original_partition = harness.published_partition_changes
            def auxiliary_report(result, root):
                if result["candidate_id"] == "accepted-3":
                    raise AttributeError("Unavailable optional partition method")
                return original_partition(result, root)
            with patch.object(harness, "published_partition_changes", side_effect=auxiliary_report):
                selected = harness.Agent().run(bridge)
            main = [(count, request) for count, request in bridge.model_inputs if "training_cells" in request]
            self.assertEqual([count for count, _ in main], [0, 1, 2])
            first, second, later = (request for _, request in main)
            self.assertEqual([first["search_intent"], second["search_intent"]], ["decoder_only", "loss_only"])
            self.assertEqual([first["parent_id"], second["parent_id"]], [baseline_id, baseline_id])
            self.assertEqual([first["parent_program"], second["parent_program"]], [initial, initial])
            first_id, second_id, third_id = (rid for rid, _ in bridge.submitted)
            first_result, second_result, third_result = (bridge.receipts[rid] for rid in (first_id, second_id, third_id))
            self.assertEqual(first_result["source"], validate_program(decoder_b, DECODER_TASK))
            self.assertEqual(second_result["source"], validate_program(loss_b, DECODER_TASK))
            initial_functions = harness.function_keys(initial)
            for result, changed in ((first_result, 1), (second_result, 0)):
                accepted = harness.function_keys(result["source"])
                self.assertEqual(initial_functions[1 - changed], accepted[1 - changed])
                self.assertNotEqual(initial_functions[changed], accepted[changed])

            last = second["last_trial"]
            self.assertEqual(last["candidate_id"], first_result["candidate_id"])
            self.assertAlmostEqual(last["score"], first_result["feedback"]["score"])
            self.assertEqual(last["initial_comparison"], {"same_as": "parent_comparison"})
            compared = last["parent_comparison"]
            self.assertTrue(compared["complete"])
            self.assertEqual(compared["scored_pairs"], 9)
            self.assertEqual(compared["parent_source"], "published_initial_reference")
            cell = next(row for row in compared["cells"] if (row["case"], str(row["seed"])) == WORST)
            self.assertGreater(cell["wns_slack_delta_ns"], 0)
            self.assertLess(cell["tns_slack_delta_ns"], 0)
            evidence = json.dumps(second["decision"]["evidence"])
            for token in (first_result["candidate_id"], *WORST):
                self.assertIn(token, evidence)
            self.assertIsNone(second["related_experiment"])
            self.assertEqual([request["evidence_brief"] for count, request in bridge.model_inputs
                              if count == 1 and "training_cells" not in request],
                             [second["decision"]["evidence"]] * 2)

            self.assertGreater(first_result["feedback"]["score"], second_result["feedback"]["score"])
            self.assertGreater(first_result["feedback"]["score"], third_result["feedback"]["score"])
            self.assertGreater(second_result["feedback"]["cells"][0]["metrics"]["native_paired_combined_score"],
                               first_result["feedback"]["cells"][0]["metrics"]["native_paired_combined_score"])
            self.assertEqual(later["parent_id"], first_result["candidate_id"])
            self.assertEqual(selected, first_result["candidate_id"])
            related = later["related_experiment"]
            self.assertEqual(related["candidate_id"], first_result["candidate_id"])
            regression = later["last_trial"]["parent_comparison"]["largest_regression"]
            self.assertEqual(related["focus"]["case"], regression["case"])
            self.assertEqual(str(related["focus"]["seed"]), str(regression["seed"]))
            self.assertIsNotNone(related["cell_score_delta_vs_parent"])

            events = [json.loads(line) for line in (folder / "search.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(event["event"] == "feedback_degraded" and event["request_id"] == third_id for event in events))
            self.assertEqual(harness.load_attempts(folder / "search.jsonl")[third_id]["policy_action"],
                             later["decision"]["reason"])
            requests = {event["call_id"]: event for event in events if event["event"] == "model_request"}
            replies = {event["call_id"]: event for event in events if event["event"] == "model_response"}
            submissions = {event["request_id"]: event for event in events if event["event"] == "submitted"}
            for rid, main_request in ((first_id, first), (second_id, second)):
                calls = submissions[rid]["model_calls"]
                ids = [calls["proposal"], *calls["alternatives"], calls["review"]]
                self.assertEqual(len(set(ids)), 3)
                self.assertTrue(set(ids) <= requests.keys() & replies.keys())
                self.assertEqual(calls["accepted_code"], calls["alternatives"][0])
                proposal = json.loads(requests[calls["proposal"]]["payload"]["input"][-1]["content"])
                self.assertEqual(proposal, main_request)
                self.assertEqual(validate_program(replies[calls["accepted_code"]]["output_text"], DECODER_TASK),
                                 bridge.receipts[rid]["source"])
                review = json.loads(requests[calls["review"]]["payload"]["input"][-1]["content"])
                self.assertEqual(validate_program(review["proposals"]["B"], DECODER_TASK), bridge.receipts[rid]["source"])
            calls = submissions[third_id]["model_calls"]
            self.assertEqual(calls["accepted_code"], calls["proposal"])
            self.assertEqual(validate_program(replies[calls["accepted_code"]]["output_text"], DECODER_TASK),
                             third_result["source"])


if __name__ == "__main__":
    unittest.main()
