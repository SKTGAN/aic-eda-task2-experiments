"""Apply the template in a temporary directory and exercise Agent.run offline."""

import copy
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from replay_feedback import diagnostic_receipts


class ReplayPause(Exception):
    """Stop the Agent after capturing a request, before an evaluation is dispatched."""


class ReplayContext:
    task = "loss_decoder"
    baseline_candidate = "frozen-initial"

    def __init__(self, framework, workspace, schedule, history, proposals=()):
        self.files = {"framework": str(framework), "workspaces": str(workspace)}
        self.evaluation_cells = schedule
        self.history = list(history)
        self.proposals = iter(proposals)
        self.requests = []
        self.pending = None
        self.enabled = True
        self.model = self

    def status(self):
        return {"history": self.history[:], "evaluation_dispatch_allowed": self.enabled,
                "model_dispatch_allowed": self.enabled, "evaluations_remaining": 5,
                "model_stop_reasons": []}

    def responses_create(self, payload):
        self.requests.append(json.loads(payload["input"][1]["content"]))
        self.pending = next(self.proposals, None)
        if self.pending is None:
            raise ReplayPause
        return {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": self.pending["source"]}]}]}

    def submit_evaluation(self, source, request_id):
        assert self.pending is not None and source == self.pending["source"]
        receipt = {**self.pending, "request_id": request_id}
        self.history.append(receipt)
        self.pending = None
        return receipt

    def wait_evaluation(self, request_id):
        return next(row for row in self.history if row["request_id"] == request_id)


def run_to_next_request(agent, context):
    try:
        agent.run(context)
    except ReplayPause:
        return context.requests[-1]
    raise AssertionError("Expected the Agent to request another proposal")


def verify(agent, framework, workspace, folder, report):
    schedule, parent, child = diagnostic_receipts(report)
    initial_path = framework / "local_tasks" / agent.DECODER_TASK / "initial_program.py"
    initial = agent.validate_program(initial_path.read_text(encoding="utf-8"), agent.DECODER_TASK)

    def sample_program(multiplier):
        line = "+ F.logsigmoid(-negative_scores).sum()"
        assert initial.count(line) == 1
        return agent.validate_program(initial.replace(line, f"{line} * {multiplier}"), agent.DECODER_TASK)

    # Use actual local timing data with synthetic receipts and proposals for this test only.
    parent.update(request_id="first", source=sample_program(0.98))
    other = {**copy.deepcopy(parent), "request_id": "second", "candidate_id": "other",
             "source": sample_program(0.99)}
    other["feedback"]["score"] -= 1
    child["source"] = sample_program(1.01)
    failed = {"candidate_id": "partial", "status": "failed", "source": sample_program(1.02),
              "feedback": {"cells": [parent["feedback"]["cells"][0],
                                     {**schedule[1], "status": "not_completed",
                                      "error_message": "test interruption"}]}}

    for receipt in (parent, other):
        agent.write_event(folder, "submitted", parent_id=ReplayContext.baseline_candidate,
                          request_id=receipt["request_id"])

    context = ReplayContext(framework, workspace, schedule, [parent, other], [child, failed])
    last_request = run_to_next_request(agent.Agent(), context)
    assert len(context.requests) == 3 and len(context.history) == 4
    root_comparison = context.requests[0]["parent_feedback"]["parent_comparison"]
    assert root_comparison == {"parent_id": ReplayContext.baseline_candidate,
                               "status": "parent_receipt_unavailable"}

    paired = last_request["parent_feedback"]["parent_comparison"]
    assert paired["parent_id"] == parent["candidate_id"]
    assert paired["complete"] and paired["scored_pairs"] == 9
    assert math.isclose(paired["official_score_delta"], report["overall"]["mean_change"])
    assert paired["largest_regression"]["case"] == "ariane133-ng45"
    assert paired["largest_regression"]["seed"] == "1001"
    assert paired["regressed_pairs"] == 4

    partial = last_request["recent_feedback"][-1]["parent_comparison"]
    assert partial["parent_id"] == child["candidate_id"] and partial["scored_pairs"] == 1
    assert partial["complete"] is False and partial["official_score_delta"] is None
    assert len(partial["candidate_unscored"]) == 8
    assert partial["candidate_unscored"][0]["reason"] == "test interruption"
    assert partial["candidate_unscored"][1]["status"] == "missing"

    logfile = folder / "search.jsonl"
    with logfile.open("ab") as log:
        log.write(b'{"event": "submitt')  # Emulate an interrupted log append.
    resumed = ReplayContext(framework, workspace, schedule, context.history)
    assert run_to_next_request(agent.Agent(), resumed) == last_request
    resumed.enabled = False
    assert agent.Agent().run(resumed) == child["candidate_id"]
    assert (folder / "program.py").read_text(encoding="utf-8") == child["source"]
    assert json.loads(logfile.read_bytes().splitlines()[-2])["event"] == "budget_stop"


def main():
    template = Path(__file__).resolve().parent
    project = template.parent
    framework = project / "official" / "contest-source" / "AgenticBench"
    source = project / "harness" / "AgenticBench" / "agent" / "loss_decoder"
    report_path = project / "official" / "contest-work" / "hard-negative-three-case-summary.json"
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))

    with TemporaryDirectory() as temporary:
        isolated = Path(temporary)
        folder = isolated / "agent"
        folder.mkdir()
        for name in ("agent.py", "prompt.md"):
            shutil.copy2(source / name, folder / name)
        shutil.copy2(template / "paired_feedback.py", folder / "paired_feedback.py")
        subprocess.run(["git", "apply", str(template / "agent-paired-feedback.patch")], cwd=folder, check=True)
        sys.path.insert(0, str(framework))
        sys.path.insert(0, str(folder))
        spec = importlib.util.spec_from_file_location("isolated_agent", folder / "agent.py")
        agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent)
        verify(agent, framework, isolated, folder, report)
    print("Offline Agent replay passed: 9 paired results, one partial receipt, resume, and final selection.")


if __name__ == "__main__":
    main()
