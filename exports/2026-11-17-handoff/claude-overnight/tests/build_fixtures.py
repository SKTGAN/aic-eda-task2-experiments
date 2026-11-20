"""Extract the completed official receipts of both server runs into tests/fixtures/server_receipts.json.

    python3 -B tests/build_fixtures.py /path/to/extracted/claude-two-server-harness-review-en

Only development material is written. Each round keeps the bridge-visible cell results, the organizer
partition diagnostic per cell, the accepted source and the lineage recorded by that server's Harness.
"""
import hashlib
import json
from pathlib import Path
import sys

archive = Path(sys.argv[1]).resolve()
servers = {}
for name in ("server-1-claude", "server-2-local-harness"):
    rounds = []
    for path in sorted((archive / name / "rounds").glob("round-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        feedback, submit = record.get("feedback_event"), record["submit_event"]
        if not feedback:
            continue  # still running when the snapshot was taken
        cells, partition = [], {}
        for cell in feedback["cells"]:
            change = cell.get("partition_change_vs_initial")
            if change is not None:
                partition[f"{cell['case']}/{cell['seed']}"] = change
            cells.append({key: cell[key] for key in ("case", "seed", "score", "raw_score", "valid", "status",
                                                      "metrics", "reason") if key in cell})
        program = (path.parent / record["candidate_program"]).resolve()
        source = program.read_text(encoding="utf-8")
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != record["source_sha256"]:
            raise ValueError(f"{program} does not match the recorded source hash")
        rounds.append({
            "round": int(path.stem.split("-")[1]),
            "request_id": record["request"]["request_id"],
            "candidate_id": record["request"]["candidate_id"],
            "status": record["request"]["status"],
            "source": source,
            "score": feedback["score"],
            "cells": cells,
            "partition": partition,
            "attempt": {key: submit[key] for key in ("parent_id", "search_intent", "changed_components")},
            "decision": submit["decision"],
        })
    servers[name] = rounds

target = Path(__file__).resolve().parent / "fixtures" / "server_receipts.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(servers, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(target, {name: [row["round"] for row in rounds] for name, rounds in servers.items()})
