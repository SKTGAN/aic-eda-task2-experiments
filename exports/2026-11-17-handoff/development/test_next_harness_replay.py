"""Offline replay against the published matrix; no model calls or physical jobs."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import diagnose_harness as dev

official = Path(sys.argv[1]).resolve()
source = official / "contest-source"
framework = source / "AgenticBench"
sys.path.insert(0, str(framework))
from contest2.agent_api import AgentAPIError
from contest2.agent_workspace import stage_agent
from contest2.controller import TASK_IDS
from contest2.sampling import validate_public_matrix
from contest2.scoring import validate_scoring_references
from grt_bench.common import write
from local_bench.matrix import LocalEvaluationMatrix
from local_bench.model import load_task

fixtures = Path(__file__).with_name("diagnostic-fixtures")
programs = {
    3: "flipped_layer_decoder.py",
    2: "criticality_excess_affinity.py",
    1: "criticality_excess_affinity_4x.py",
}
spec = load_task(framework / "local_tasks" / TASK_IDS[dev.BASELINE])
full = LocalEvaluationMatrix(official / "contest-data/task2/loss_decoder/train/qualified_matrix.json", spec)
validate_public_matrix(full, dev.BASELINE, "train")
validate_scoring_references(full, dev.BASELINE)
table = json.loads((framework / "contest2/manifests/common-timing-reference.json").read_text(encoding="utf-8"))
with TemporaryDirectory() as temporary:
    work = Path(temporary)
    for n in (1, 2):
        matrix_file = work / f"{n}.json"
        panel = dev.select_panel(table, n)
        write(matrix_file, dev.make_matrix(full, panel))
        matrix = LocalEvaluationMatrix(matrix_file, spec)
        assert len(matrix.cells) == n * 3
        assert {(c["case"], c["seed"]) for c in matrix.cells} == {
            (case, row["seed"]) for case, rows in panel.items() for row in rows}
        if n == 1:
            first_matrix = matrix
    agent_dir = stage_agent(dev.HERE.parent / "next-harness/AgenticBench/agent/loss_decoder", work / "agent")
    sys.path.insert(0, str(agent_dir))
    import agent
    from local_tasks.tp_gnn_local_task_definitions import validate_program
    def result_text(answer):
        return {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": answer}]}]}
    model = dev.DiagnosticModel("", "", work / "model.jsonl", AgentAPIError, "high")
    model.passthrough = True
    ledger = SimpleNamespace(snapshot=lambda: {"model_dispatch_allowed": True, "model_stop_reasons": []})
    context = dev.DiagnosticContext(first_matrix, source, work, None, ledger, model)
    calls, physical = [], []
    winning = {"status": "succeeded", "candidate_id": "winning"}
    broad = {"parent_comparison": {"complete": True, "official_score_delta": 1,
             "cells": [{"case": x, "score_delta": 1} for x in ("a", "b", "c")]}}
    parent, intent, reason = agent.select_parent([winning], winning, [broad], None)
    assert parent is winning and intent == "decoder_only" and reason["reason"] == "refine_supported_opening"
    uncertain = {**broad, "timing_changes_with_identical_assignment": [{"case": "a"}]}
    parent, intent, reason = agent.select_parent([winning], winning, [uncertain], None)
    assert parent is None and intent == "loss_only" and reason["reason"] == "test_alternative_component_after_opening"
    def fake_send(payload, purpose):
        request = json.loads(payload["input"][1]["content"])
        calls.append((purpose, payload["reasoning"]["effort"], request))
        assert len(calls) < 24, request.get("previous_generation_issue")
        if purpose == "plan":
            assert agent.PLAN_TASK in payload["input"][0]["content"]
            present = agent.EXPERIENCE_HEADING in payload["input"][0]["content"]
            assert present == (request["evaluations_remaining"] == 3)
            answer = "Change one decision and check the resulting WNS and TNS."
        else:
            assert request["experiment_plan"]
            assert agent.EXPERIENCE_HEADING not in payload["input"][0]["content"]
            assert "recent_feedback" not in request
            candidate = (fixtures / programs[request["evaluations_remaining"]]).read_text(encoding="utf-8")
            answer = validate_program(candidate, spec.task_id)
        return result_text(answer), answer
    def fake_evaluate(candidate_dir, source_path, output, **kwargs):
        assert kwargs["workers"] == 1
        assert (candidate_dir / "candidate.json").is_file()
        score = (-20, 40, 45)[len(physical)]
        physical.append(output.name)
        rows = [{"case": c["case"], "seed": c["seed"], "status": "succeeded", "score": score, "valid": True,
                 "metrics": {"final_global_wns_setup_ns": -.2, "final_global_tns_setup_ns": -1.2}}
                for c in context.matrix.cells]
        return SimpleNamespace(metrics={"combined_score": score, "valid": True, "matrix": {
            "matrix_sha256": context.matrix.identity, "expected_cells": 3,
            "complete": True, "qualification": False, "cases": {}, "cells": rows}})
    with patch.object(model, "send", fake_send), patch.object(first_matrix, "evaluate", fake_evaluate):
        selected = agent.Agent().run(context)
    assert len(physical) == 3
    assert len(calls) == 6
    assert context.receipts[physical[-1]]["candidate_id"] == selected
    assert all(row["status"] == "succeeded" for row in context.receipts.values())
    analyses = [row for row in calls if row[0] == "plan"]
    generates = [row for row in calls if row[0] == "candidate_generation"]
    assert [row[1] for row in analyses] == ["high"] * 3
    assert [row[1] for row in generates] == ["low"] * 3
    assert len(analyses[1][2]["incumbent_feedback"]["cells"]) == 3
    assert len(analyses[2][2]["parent_feedback"]["cells"]) == 3
    for row in (analyses[1][2]["incumbent_feedback"], analyses[2][2]["parent_feedback"]):
        for cell in row["cells"]:
            assert "final_global_wns_setup_ns" in cell["metrics"]
            assert "final_global_tns_setup_ns" in cell["metrics"]
print("PASS: official 3- and 6-cell matrix contracts, 3 simulated candidates, WNS/TNS feedback opening decision gates, expert isolation and two model calls per candidate")
