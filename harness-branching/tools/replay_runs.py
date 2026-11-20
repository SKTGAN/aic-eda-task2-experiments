"""Replay each observed training prefix independently; never execute a candidate or a model."""

import argparse
import base64
import io
import json
from pathlib import Path
from statistics import mean
import sys
from zipfile import ZipFile


HARNESS = Path(__file__).resolve().parents[1]
PROJECT = HARNESS.parent
EXPORTS = PROJECT / "exports"
sys.path.insert(0, str(PROJECT / "official/contest-source/AgenticBench"))
sys.path.insert(0, str(HARNESS / "AgenticBench/agent/loss_decoder"))

from contest2.scoring import reference_table, score_metrics
from paired_feedback import compare_feedback
from search_control import select_next


def read_capture(path):
    with ZipFile(io.BytesIO(base64.b64decode(path.read_bytes()))) as archive:
        ledger = json.loads(archive.read("capture.json"))["evaluations"]
        events = (json.loads(line) for line in archive.read(
            "participant-agent/loss_decoder/search.jsonl").splitlines() if line.strip())
        by_request = {event["request_id"]: event for event in events if event.get("event") == "evaluated"}
        rows = []
        for entry in ledger:
            if entry["status"] != "succeeded":
                continue
            row = by_request[entry["request_id"]]
            if entry["candidate_id"] != row["candidate_id"]:
                raise ValueError("Capture and search log disagree on candidate identity")
            rows.append(row)
        return rows


def compact_cell(cell):
    metrics = {"final_global_wns_setup_ns": cell.get("wns"), "final_global_tns_setup_ns": cell.get("tns")}
    return {"case": cell["case"], "seed": str(cell["seed"]), "score": cell["score"],
            "status": cell.get("status") or ("succeeded" if cell["valid"] is True else "unknown"),
            "valid": cell["valid"], "raw_score": cell.get("raw"), "metrics": metrics}


def read_compact(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return [{"candidate_id": row["candidate"], "status": "succeeded", "score": row["score"],
             "cells": [compact_cell(cell) for cell in row["cells"]],
             "attempt": {"parent_id": row["parent"], "search_intent": row["intent"],
                         "changed_components": row["edits"]}}
            for row in data["rounds"]]


def as_receipt(row):
    return {"candidate_id": row["candidate_id"], "status": row["status"],
            "feedback": {"score": row["score"], "cells": row["cells"]}}


def reference(schedule, baseline_id):
    table = reference_table()["cases"]
    cells = []
    for pair in schedule:
        case, seed = pair["case"], str(pair["seed"])
        item = table[case]["measurements"]["loss_decoder"][seed]
        metrics = score_metrics(case, {"runs_successfully": 1, "sta_graph_complete": 1,
            "timing_evaluation_boundary": "post-opt-pre-cts", "combined_score": 0,
            "final_global_wns_setup_ns": item["wns_ns"], "final_global_tns_setup_ns": item["tns_ns"]})
        cells.append(dict(case=case, seed=seed, status="published_reference",
                          score=metrics["combined_score"], metrics=metrics))
    return {"candidate_id": baseline_id, "status": "published_reference",
            "feedback": {"score": mean(cell["score"] for cell in cells), "cells": cells}}


def replay(rows, schedule):
    baseline = rows[0]["attempt"]["parent_id"]
    receipts = {baseline: reference(schedule, baseline)}
    labels = {baseline: "initial"}
    history, decisions = [], []
    keys = {(cell["case"], str(cell["seed"])) for cell in schedule}
    for prefix_size in range(len(rows) + 1):
        incumbent = max(history, key=lambda row: row["score"]) if history else None
        next_parent, intent, decision = select_next(history, baseline, None, schedule,
            incumbent_id=incumbent["candidate_id"] if incumbent else None)
        entry = {"after_round": prefix_size, "incumbent": labels[incumbent["candidate_id"]] if incumbent else None,
                 "best_observed_score": incumbent["score"] if incumbent else None,
                 "planner_parent": labels[next_parent], "planner_intent": intent, "decision": decision}
        decisions.append(entry)
        if prefix_size == len(rows):
            break
        trial = dict(rows[prefix_size])
        cells = trial["cells"]
        if len(cells) != len(keys) or {(cell["case"], str(cell["seed"])) for cell in cells} != keys:
            raise ValueError("Partial or different train matrix")
        parent = trial["attempt"]["parent_id"]
        receipt = as_receipt(trial)
        if trial.get("parent_comparison") is None:
            trial["parent_comparison"] = compare_feedback(receipts[parent], receipt, schedule, partition_changes={})
        entry["actual_next_parent"] = labels[parent]
        entry["actual_next_edit"] = sorted(trial["attempt"]["changed_components"])
        labels[trial["candidate_id"]] = prefix_size + 1
        receipts[trial["candidate_id"]] = receipt
        history.append(trial)
    return {"observed_complete_rounds": len(rows), "prefixes": decisions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matrix = PROJECT / "official/contest-data/task2/loss_decoder/train/qualified_matrix.json"
    schedule = [{"case": cell["case"], "seed": str(cell["seed"])}
                for cell in json.loads(matrix.read_text(encoding="utf-8"))["cells"]]
    sources = {
        "original": (read_capture, EXPORTS / "2026-11-17-claude/ours-before-stop.capture"),
        "claude": (read_compact, EXPORTS / "2026-11-18-overnight/claude-formal-vs-official-reference.json"),
        "evidence": (read_compact, EXPORTS / "2026-11-18-overnight/evidence-formal-prefix.json"),
    }
    output = args.output.resolve()
    if HARNESS == output or HARNESS in output.parents or any(output == path.resolve() for _, path in sources.values()):
        raise ValueError("Output must be outside the Harness and must not replace a source artifact")
    report = {"mode": "offline_observed_prefixes", "notes": [
        "Each decision uses only preceding real training results. Subsequent scores belong to the actual historical choices.",
        "Timing agreement never establishes partition agreement. Compact exports do not provide aligned assignments.",
        "The final prefix decision is a diagnostic only, including after the formal budget has been exhausted."],
        "runs": {}}
    for label, (loader, path) in sources.items():
        report["runs"][label] = dict(source=str(path.relative_to(PROJECT)), **replay(loader(path), schedule))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for label, run in report["runs"].items():
        print(label, run["observed_complete_rounds"], [step["decision"]["reason"] for step in run["prefixes"]])


if __name__ == "__main__":
    main()
