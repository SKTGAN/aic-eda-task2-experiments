"""Run both published splits for one fixed program and report the local 15-cell mean."""
import argparse
import fcntl
import json
import math
import subprocess
import sys
from pathlib import Path
from statistics import mean


TOOLS = Path(__file__).resolve().parents[1] / "score-challenge-20261118"
sys.path.insert(0, str(TOOLS))
from measure_development_panel import read, require, source_digest


def write(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def measure(official, output, candidate, source, order):
    from contest2.scoring import PUBLIC_SPLITS, SEEDS

    digest = source_digest(source)
    directory = output / "sources" / digest
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = directory / candidate.name
    if snapshot.exists():
        require(snapshot.read_text(encoding="utf-8") == source, "Archived program differs from its source")
    else:
        temporary = snapshot.with_suffix(".tmp")
        temporary.write_text(source, encoding="utf-8")
        temporary.replace(snapshot)
    prefix = f"{candidate.stem}-{digest[:12]}"
    result = output / (prefix + "-fifteen.json")
    image = read(official / "contest-data/task2/runtime.json")["image"]
    report = {"scope": "local development on all five published designs", "candidate_sha256": digest, "status": "running",
              "candidate_source": str(snapshot), "official_root": str(official), "image": image,
              "complete": False, "score_fifteen": None, "case_means": {}, "splits": {}, "cells": []}
    for split in order:
        keys = [f"{case}/{seed}" for case in PUBLIC_SPLITS[split] for seed in SEEDS]
        panel_dir = output / "panels"
        panel_id = source_digest("\n".join(sorted(keys)))[:12]
        panel = panel_dir / f"{prefix}-{panel_id}.json"
        report.update(active_split=split, active_panel=str(panel))
        write(result, report)
        command = [sys.executable, "-B", "-u", str(TOOLS / "measure_development_panel.py"),
                   "--official", str(official), "--candidate", str(snapshot), "--output", str(panel_dir),
                   "--split", split, "--cells", *keys]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as error:
            report.update(status="stopped", panel_exit_code=error.returncode)
            write(result, report)
            raise
        card = read(panel)
        rows = card["cells"]
        actual = [f"{row['case']}/{row['seed']}" for row in rows]
        require(card["complete"] and card["candidate_sha256"] == digest and card["image"] == image
                and card["split"] == split and actual == keys and all(row["status"] in ("succeeded", "penalized") for row in rows)
                and math.isclose(mean(row["score"] for row in rows), card["panel_score"], abs_tol=1e-10),
                f"Unexpected native panel {panel}")
        report["cells"].extend({"split": split, **row} for row in rows)
        report["case_means"].update(card["case_means"])
        report["splits"][split] = {"count": len(rows), "score": card["panel_score"], "panel": str(panel),
                                   "matrix_sha256": card["published_matrix_sha256"]}
    rows = report["cells"]
    require(len(rows) == 15 and len(report["case_means"]) == 5, "Expected five designs and 15 results")
    value = mean(row["score"] for row in rows)
    require(math.isclose(value, mean(report["case_means"].values()), abs_tol=1e-10), "Unequal case weights")
    report.update(status="complete", complete=True, active_split=None, active_panel=None, score_fifteen=value)
    write(result, report)
    print(f"{candidate.stem}: {len(rows)}/15, mean {value:.6f} -> {result}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("official", "candidate", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--validation-first", action="store_true", help="Start with the six public validation cells")
    args = parser.parse_args()
    official = args.official.resolve(strict=True)
    output = args.output.resolve()
    require(output != official and official not in output.parents, "Choose an output outside the official installation")
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(official / "contest-source/AgenticBench"))
    candidate = args.candidate.resolve(strict=True)
    source = candidate.read_text(encoding="utf-8")
    order = ("validation", "train") if args.validation_first else ("train", "validation")
    with (output / (source_digest(source) + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        measure(official, output, candidate, source, order)


if __name__ == "__main__":
    main()
