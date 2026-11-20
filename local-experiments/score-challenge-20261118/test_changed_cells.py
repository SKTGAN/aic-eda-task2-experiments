"""Use measured changes to screen variants, and require a native nine-cell run for a win."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
from statistics import mean
import subprocess
import sys

HERE = Path(__file__).resolve().parent
DRIVER = HERE.parent / "bp-boundary-20261118/measure_train_score.py"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(source):
    return hashlib.sha256(source.read_text(encoding="utf-8").encode()).hexdigest()


def changes_for(name, folder, nine):
    if name == "guarded_adjacent":
        data = read(folder / "guarded-adjacent-vs-variance-guard-nine-cell.json")
        candidate_hash = data["candidate_sha256"][name]
        counts = {(row["case"], row["seed"]): row["postclosure_difference"]["direct"]
                  for row in data["cells"]}
    elif name == "guard_orientation":
        data = read(folder / "capacity-and-guard-orientation-replay.json")
        candidate_hash = data["guard_oriented_program_sha256"]
        counts = {(row["case"], row["seed"]): row["parents"]["variance_guard"]["postclosure_changed"]
                  for row in data["cells"]}
    else:
        raise ValueError(f"No paired assignment evidence for {name}")
    if not data["complete"] or set(counts) != nine or candidate_hash != digest(HERE / (name + ".py")):
        raise ValueError(f"Incomplete or mismatched geometry evidence for {name}")
    return sorted((case, seed) for (case, seed), count in counts.items() if count)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--after-candidate", type=Path, help="Skip backup probes if this candidate already met the target")
    args = parser.parse_args()
    output = args.output.resolve(strict=True)
    # Wait for the parent to finish before making an inference from its receipts.
    with (args.official / "contest-work/local-followup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        parent = read(output / "variance_guard-train.json")
        if args.after_candidate:
            candidate = args.after_candidate.resolve(strict=True)
            card_path = output / (candidate.stem + "-train.json")
            if card_path.exists():
                card = read(card_path)
                cells = {(r["case"], r["seed"]) for r in card["cells"]}
                expected = {(r["case"], r["seed"]) for r in parent["cells"]}
                if (len(cells) == len(card["cells"]) == 9 and cells == expected
                        and card["image"] == parent["image"] and card["candidate_sha256"] == digest(candidate)
                        and mean(r["score"] for r in card["cells"]) > parent["benchmark"]):
                    print(f"{candidate.stem} exceeded the target, backup evaluations complete", flush=True)
                    return
    if parent["full_score"] is None or parent["candidate_sha256"] != digest(HERE / "variance_guard.py"):
        raise ValueError("Parent must have an actual nine-cell result")
    target = parent["benchmark"]
    if parent["full_score"] > target:
        print("Parent already exceeds the target", flush=True)
        return
    base = {(r["case"], r["seed"]): r["score"] for r in parent["cells"]}
    if len(base) != 9:
        raise ValueError("Expected nine distinct training cells")
    for name in ("guarded_adjacent", "guard_orientation"):
        changed = changes_for(name, output, set(base))
        command = [sys.executable, "-B", "-u", str(DRIVER), "--official", str(args.official),
                   "--output", str(output), "--candidate", str(HERE / (name + ".py"))]
        estimated = dict(base)
        measured = []
        for case, seed in sorted(changed, key=lambda cell: (cell[0] != "bp_fe-ng45", -cell[1])):
            subprocess.run(command + ["--train-cell", f"{case}/{seed}"], check=True)
            card = read(output / f"{name}-{case}-{seed}.json")
            row = card["cells"][0]
            if card["image"] != parent["image"] or (row["case"], row["seed"]) != (case, seed):
                raise ValueError("Unexpected receipt for candidate probe")
            estimated[(case, seed)] = row["score"]
            measured.append(row)
        projected = mean(estimated.values())
        report = {"scope": "development screen only, not a full candidate training score",
                  "measured_changed_cells": measured, "other_cells_assumed_to_repeat_parent": 9 - len(measured),
                  "conditional_mean": projected, "benchmark": target,
                  "promoted_for_full_measurement": projected > target}
        (output / (name + "-screen.json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"{name} {len(measured)} measured changes; conditional mean {projected:.5f}", flush=True)
        if projected > target:
            subprocess.run(command + ["--stop-if-out"], check=True)
            full = read(output / (name + "-train.json"))["full_score"]
            if full is not None and full > target:
                print(f"{name} actual nine-cell score {full:.5f}", flush=True)
                return


if __name__ == "__main__":
    main()
