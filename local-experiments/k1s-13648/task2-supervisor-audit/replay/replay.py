"""Replay the first two rounds of a recorded run through an Agent directory and capture its round-3 request.

    python3 -I -B replay/replay.py <agent_dir> <window_dir> <out_dir> [--opening loss_only|decoder_only]

<window_dir> holds round-01/ and round-02/ from one historical run (the BLIND_R2_ONLY windows), each with
candidate.py, generation.json and receipt.json. Nothing here is part of the Agent.

- The bridge returns the recorded official receipts: every metric of the official nine-cell matrix, the
  official score, and the organizer partition diagnostics as native per-cell result files.
- The scripted model returns the recorded candidates. For the opening alternative it returns the run's own
  recorded alternatives when the run had any. Otherwise it echoes proposal A, which the Agent rejects as a
  repeat, so no extra proposal enters the replay.
- The opening review answers PICK A, as every recorded review did.
- The Agent's next generation request after the second evaluation is written to <out_dir>. The replay then
  stops the Agent process before any third submission. A step that needs no model call (a shelved
  proposal, a recombination or a resubmission) is captured at its submission instead.
- With --continue <round_dir>, that request is answered with the recorded candidate of a later round and
  evaluated with its recorded receipt, and the replay stops at the following request instead. This is
  used only to exercise the code paths after round 3 with a real receipt. The later candidate was written
  under another Harness, so its score is not what this Agent's round 3 would have scored.

Scores, partitions and replies are therefore exactly the recorded ones. What differs between Agent
directories is only what each Agent decides and sends.
"""

import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tests"))
import support  # noqa: E402

GENERATION, ALTERNATIVE, REVIEW = "generation", "opening_alternative", "opening_review"
NATIVE_PARTITION_FIELDS = ("partition_assignment_identical", "partition_assignment_changed_count",
                           "partition_assignment_changed_fraction", "tp_gnn_repair_moved_area_fraction")


def normalized(source):
    return source.strip() + "\n"


def load_round(folder):
    folder = Path(folder)
    receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
    return {"name": folder.name, "source": normalized((folder / "candidate.py").read_text(encoding="utf-8")),
            "receipt": receipt, "intent": receipt["overview"]["search_intent"], "alternatives": []}


def load_window(window_dir):
    """The recorded rounds: candidate source, official receipt and recorded alternatives per round."""
    rounds = []
    for folder in sorted(Path(window_dir).glob("round-*")):
        receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
        generation = json.loads((folder / "generation.json").read_text(encoding="utf-8"))
        alternatives = generation.get("associated_call_ids", {}).get("alternatives") or []
        replies = {}
        for event in generation["generation_events"]:
            body = event["event"]
            if body.get("event") == "model_response":
                replies[body["call_id"]] = body.get("output_text") or ""
        rounds.append({
            "name": folder.name,
            "source": normalized((folder / "candidate.py").read_text(encoding="utf-8")),
            "receipt": receipt,
            "intent": receipt["overview"]["search_intent"],
            "alternatives": [replies[call] for call in alternatives if call in replies],
        })
    return rounds


def official_parent_program(window_dir):
    """The official initial program exactly as the recorded run sent it to the model."""
    folder = sorted(Path(window_dir).glob("round-*"))[0]
    generation = json.loads((folder / "generation.json").read_text(encoding="utf-8"))
    for event in generation["generation_events"]:
        body = event["event"]
        if body.get("event") == "model_request":
            request = json.loads(body["payload"]["input"][1]["content"])
            return normalized(request["parent_program"])
    raise ValueError("no recorded request carries the parent program")


def bridge_result(round_record, request_id, source, evaluations_root):
    """The official reply for a recorded round, in the shape the contest bridge returns."""
    receipt = round_record["receipt"]
    matrix = receipt["official_receipt"]["matrix"]
    artifacts = Path(evaluations_root) / request_id
    cells = []
    for cell in matrix["cells"]:
        metrics = dict(cell["metrics"])
        cells.append({"case": cell["case"], "seed": int(cell["seed"]), "status": cell["status"],
                      "valid": cell["valid"], "score": cell["score"], "raw_score": cell["raw_score"],
                      "metrics": metrics})
        native = artifacts / "cells" / cell["case"] / str(cell["seed"]) / "result"
        native.mkdir(parents=True, exist_ok=True)
        (native / "evaluation_result.json").write_text(json.dumps({"metrics": {
            key: metrics[key] for key in NATIVE_PARTITION_FIELDS if key in metrics}}), encoding="utf-8")
    return {"request_id": request_id, "candidate_id": receipt["overview"]["candidate_id"],
            "status": receipt["overview"]["status"], "reason": "", "source": source,
            "artifacts_dir": str(artifacts),
            "feedback": {"score": receipt["official_receipt"]["metrics"]["combined_score"], "cells": cells}}


class Stop(support.ProcessStopped):
    """The replay ends here: the Agent's next step has been captured."""


class ReplayBridge(support.MockBridge):
    def __init__(self, workdir, rounds, initial_program, evaluation_limit=10, model_limit=80, followups=()):
        self.rounds = rounds
        self.followups = list(followups)
        self.later = []                 # generation requests after the openings, in order
        self.consumed = list(followups)
        self.captured = self.stopped = None
        super().__init__(workdir, world=None, persona=self._persona, evaluation_limit=evaluation_limit,
                         model_limit=model_limit)
        task = Path(self.files["framework"]) / "local_tasks" / support.DECODER_TASK
        (task / "initial_program.py").write_text(initial_program, encoding="utf-8")
        self.alternatives = {record["intent"]: list(record["alternatives"]) for record in rounds}

    @staticmethod
    def entry(system):
        if system.startswith("Write a competing opening experiment"):
            return ALTERNATIVE
        if system.startswith("Review these opening proposals"):
            return REVIEW
        return GENERATION

    def _persona(self, system, request):
        kind = self.entry(system)
        if kind == REVIEW:
            return "PICK A"
        if kind == ALTERNATIVE:
            recorded = self.alternatives.get(request.get("search_intent")) or []
            if recorded:
                return recorded.pop(0)
            return "```python\n" + request["proposal_a"] + "```"
        decision = request.get("decision") or {}
        if decision.get("reason") == "opening_control":
            for record in self.rounds:
                if record["intent"] == request.get("search_intent"):
                    return "```python\n" + record["source"] + "```"
        self.later.append({"system": system, "request": request, "model_call": self.model_calls})
        if self.captured is None:
            self.captured = {"kind": "generation_request", "system": system, "request": request,
                             "model_call": self.model_calls}
        if self.followups:
            return "```python\n" + self.followups.pop(0)["source"] + "```"
        raise Stop("generation request captured")

    def submit_evaluation(self, source, request_id=None):
        self.submit_calls.append({"request_id": request_id, "source": source})
        if request_id in self.records:
            return self.records[request_id]
        record = next((record for record in self.rounds + self.consumed if record["source"] == normalized(source)),
                      None)
        if record is None:
            self.stopped = {"kind": "submission_without_model_call", "request_id": request_id, "source": source,
                            "after_evaluations": len(self.order)}
            if self.captured is None:
                self.captured = self.stopped
            raise Stop("submission captured before evaluation")
        result = bridge_result(record, request_id, source, self.files["evaluations"])
        self.records[request_id] = result
        self.order.append(request_id)
        return result


def run(agent_dir, window_dir, workdir, opening=None, followups=()):
    """Run one Agent directory through the recorded rounds. Returns (bridge, agent copy directory)."""
    rounds = load_window(window_dir)
    agent, copy = support.load_agent(agent_dir, workdir)
    if opening:
        (copy / "opening.txt").write_text(opening + "\n", encoding="utf-8")
    later = [load_round(folder) for folder in followups]
    bridge = ReplayBridge(workdir, rounds, official_parent_program(window_dir), followups=later)
    try:
        agent.Agent().run(bridge)
    except Stop:
        pass
    return bridge, copy


def events(copy):
    path = Path(copy) / "search.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_capture(bridge, copy, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for index, request in enumerate(bridge.requests, 1):
        (out / "call-{:02d}-{}.json".format(index, ReplayBridge.entry(request["system"]))).write_text(
            json.dumps({"system": request["system"], "user": request["user"]}, indent=1, ensure_ascii=False),
            encoding="utf-8")
    captured = bridge.captured or {"kind": "nothing_captured"}
    (out / "round3.json").write_text(json.dumps(captured, indent=1, ensure_ascii=False), encoding="utf-8")
    if captured.get("kind") == "generation_request":
        (out / "round3-system.txt").write_text(captured["system"], encoding="utf-8")
        (out / "round3-request.json").write_text(json.dumps(captured["request"], indent=1, ensure_ascii=False),
                                                encoding="utf-8")
    if bridge.stopped is not None:
        (out / "stopped-at-submission.json").write_text(json.dumps(bridge.stopped, indent=1, ensure_ascii=False),
                                                       encoding="utf-8")
    for index, later in enumerate(bridge.later[1:], 4):
        (out / "round{}-request.json".format(index)).write_text(
            json.dumps(later["request"], indent=1, ensure_ascii=False), encoding="utf-8")
    shutil.copy(Path(copy) / "search.jsonl", out / "search.jsonl")
    for dossier in Path(copy).glob("supervisor-dossier-*.json"):
        shutil.copy(dossier, out / dossier.name)
    return captured


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    agent_dir, window_dir, out_dir = argv[1:4]
    opening = argv[argv.index("--opening") + 1] if "--opening" in argv else None
    followups = [argv[argv.index("--continue") + 1]] if "--continue" in argv else []
    workdir = support.make_workdir()
    bridge, copy = run(agent_dir, window_dir, workdir, opening, followups)
    captured = write_capture(bridge, copy, out_dir)
    print(json.dumps({"captured": captured.get("kind"), "model_calls": bridge.model_calls,
                      "evaluations": len(bridge.order),
                      "round3_parent_id": (captured.get("request") or {}).get("parent_id"),
                      "round3_intent": (captured.get("request") or {}).get("search_intent"),
                      "round3_decision": (captured.get("request") or {}).get("decision")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
