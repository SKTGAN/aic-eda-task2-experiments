"""Extract the complete official receipts of the three-server archive into tests/fixtures/three_servers.json.

    python3 -I tests/build_three_server_fixtures.py /path/to/extracted/claude-three-server-harness-review-en

Development material only. Each round keeps the bridge-visible cells (with their organizer partition
diagnostics), the accepted source (checked against its recorded hash) and the lineage recorded by that
run's Harness.
"""
import hashlib
import json
from pathlib import Path
import sys

archive = Path(sys.argv[1]).resolve()
runs = {}
for name in ("claude-original", "claude-new", "ours-new"):
    rounds = []
    for path in sorted((archive / name / "rounds").glob("round-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("finished_cells") != record.get("expected_cells") or record.get("score") is None:
            continue
        bridge = record.get("diagnostic_bridge_feedback") or {}
        if not bridge.get("cells"):
            # No bridge capture: rebuild the bridge-visible cells from the physical cell summaries and the
            # organizer's native per-cell results (the bridge forwards those native metrics).
            cells = []
            for cell in record["physical_cells"]:
                native = json.loads((archive / name / cell["raw_receipt"]).read_text(encoding="utf-8"))
                cells.append({"case": cell["case"], "seed": str(cell["seed"]), "score": cell["score"],
                              "raw_score": cell.get("raw_score"), "valid": cell["valid"], "status": cell["status"],
                              "metrics": native["metrics"]})
            bridge = {"score": record["score"], "cells": cells}
        source = (archive / name / record["program"]).read_text(encoding="utf-8")
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != record["program_sha256"]:
            raise ValueError(f"{path}: program does not match its recorded hash")
        cells, partition = [], {}
        for cell in bridge["cells"]:
            metrics = cell.get("metrics") or {}
            partition[f"{cell['case']}/{cell['seed']}"] = {
                key: metrics[key] for key in ("partition_assignment_identical", "partition_assignment_changed_count",
                                              "partition_assignment_changed_fraction",
                                              "tp_gnn_repair_moved_area_fraction") if key in metrics}
            cells.append({key: cell[key] for key in ("case", "seed", "score", "raw_score", "valid", "status",
                                                      "metrics", "reason") if key in cell})
        decision = record["submitted_search_decision"]
        rounds.append({
            "round": record["round"],
            "request_id": record["request"]["request_id"],
            "candidate_id": record["request"]["candidate_id"],
            "status": record["request"]["status"],
            "source": source,
            "score": bridge["score"],
            "cells": cells,
            "partition": partition,
            "attempt": {key: decision[key] for key in ("parent_id", "search_intent", "changed_components")},
            "decision": decision.get("decision"),
        })
    runs[name] = rounds

target = Path(__file__).resolve().parent / "fixtures" / "three_servers.json"
target.write_text(json.dumps(runs, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(target, {name: [row["round"] for row in rounds] for name, rounds in runs.items()})
