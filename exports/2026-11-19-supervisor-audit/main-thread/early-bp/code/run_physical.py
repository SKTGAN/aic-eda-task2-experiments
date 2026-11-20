"""Paired local-only decoder experiment. Uses saved, matched stock runs as controls."""
import argparse
import csv
import fcntl
import json
from pathlib import Path
import subprocess
import sys


EXPERIMENT = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPERIMENT.parent))
from run_local_followup import run_trial, verified_trial


def assignments(root, mode, seed):
    cell = root / mode / "cells" / "bp-ng45" / seed / "result"
    for relative in ("run/20_partition/partition_assignment.csv",
                     "retained_artifacts/algorithm/20_partition/partition_assignment.csv"):
        path = cell / relative
        if path.is_file():
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            values = {row["inst_name"]: row["die"] for row in rows}
            if values and len(values) == len(rows) and set(values.values()) == {"top", "bottom"}:
                return values
    raise ValueError("Missing verified instance assignments: " + str(cell))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", default=["1002", "1003", "1001"], choices=["1001","1002","1003"])
    parser.add_argument("--candidate", default="boundary_decoder", choices=["boundary_decoder", "residual_decoder", "negative_second_moment"])
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()
    official = args.official.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (official / "contest-work/local-followup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for seed in args.seeds:
            if not verified_trial(official, "bp-ng45", seed, None):
                raise RuntimeError("No same-host completed control for " + seed)
        for seed in args.seeds:
            initial = verified_trial(official, "bp-ng45", seed, None)
            program = EXPERIMENT / (args.candidate + ".py")
            if args.collect_only:
                candidate = verified_trial(official, "bp-ng45", seed, program)
                if not candidate:
                    raise RuntimeError("No completed candidate to collect for " + seed)
            else:
                candidate = run_trial(official, output, args.candidate, "bp-ng45", seed, program)
            raw = subprocess.check_output([sys.executable, "-B", str(EXPERIMENT.parent / "compare_trials.py"),
                                          str(initial), str(candidate)], text=True)
            report = json.loads(raw)
            try:
                before = assignments(initial, "baseline/qualification", seed)
                after = assignments(candidate, "evaluation", seed)
                if before.keys() != after.keys():
                    raise ValueError("Instance sets differ")
                changed = sum(value != after[key] for key, value in before.items())
                report["matched_assignment"] = {"instance_count": len(before), "literal_changed": changed,
                                                "after_best_global_flip": min(changed, len(before)-changed)}
            except (OSError, ValueError, KeyError) as error:
                report["assignment_unavailable"] = str(error)
            destination = output / (args.candidate + "-physical-" + seed + ".json")
            pending = destination.with_suffix(".tmp")
            pending.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
            pending.replace(destination)
            print(seed, report.get("matched_assignment"), report["change"]["final_global_tns_setup_ns"],
                  report["change"]["common_reference_score"], flush=True)


if __name__ == "__main__":
    main()
