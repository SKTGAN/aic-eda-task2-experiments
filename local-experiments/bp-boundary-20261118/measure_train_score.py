"""Measure the fixed local candidate against the published nine-cell train split."""
import argparse
import fcntl
import hashlib
import json
import sys
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from compare_trials import read_trial
from run_local_followup import run_trial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--stop-if-out", action="store_true", help="Stop when even perfect remaining cells cannot exceed the benchmark")
    parser.add_argument("--probe", action="store_true", help="Measure the same three diagnostic training cells for every challenger")
    parser.add_argument("--train-cell", help="Measure one named case/seed from the training split")
    parser.add_argument("--new-cells-first", action="store_true", help="Begin with the six cells outside the three-cell development panel")
    parser.add_argument("--first-training-cell", action="append", help="Prioritize a training cell; repeat for ordered probes")
    parser.add_argument("--if-needed", action="store_true", help="Skip a queued challenger if another local code already has nine verified scores above the target")
    args = parser.parse_args()
    official = args.official.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(official / "contest-source/AgenticBench"))
    from contest2.scoring import PUBLIC_SPLITS, SEEDS, score_metrics

    candidate = args.candidate.resolve(strict=True) if args.candidate else HERE / "negative_second_moment.py"
    digest = hashlib.sha256(candidate.read_text(encoding="utf-8").encode()).hexdigest()
    original_results = HERE.parents[1] / "exports/2026-11-18-bp-local"
    settings = json.loads((original_results / "new-loss-scorecard.json").read_text())
    if not args.candidate and digest != settings["candidate_sha256"]:
        raise ValueError("Candidate differs from the three measured bp cells")
    train = PUBLIC_SPLITS["train"]
    ordered_cases = ["bp-ng45"] + [case for case in train if case != "bp-ng45"]
    cells = [(case, seed) for case in ordered_cases for seed in SEEDS]
    if args.candidate:
        priority = [("bp_fe-ng45", 1001), ("ariane133-ng45", 1001), ("bp-ng45", 1002)]
        full_priority = priority + [("bp_fe-ng45", 1002), ("ariane133-ng45", 1002)]
        cells = priority if args.probe else full_priority + [cell for cell in cells if cell not in full_priority]
        if args.new_cells_first and not args.probe:
            cells = [cell for cell in cells if cell not in priority] + priority
    if args.first_training_cell:
        by_name = {f"{case}/{seed}": (case, seed) for case, seed in cells}
        if any(key not in by_name for key in args.first_training_cell) or len(set(args.first_training_cell)) != len(args.first_training_cell):
            parser.error("Priority cells must be unique members of the current panel")
        matches = [by_name[key] for key in args.first_training_cell]
        cells = matches + [cell for cell in cells if cell not in matches]
    if args.train_cell:
        if args.probe or not args.candidate:
            parser.error("--train-cell requires a candidate and cannot be combined with --probe")
        cells = [cell for cell in cells if args.train_cell == f"{cell[0]}/{cell[1]}"]
        if len(cells) != 1:
            parser.error("Unknown training cell")
    benchmark_file = original_results.parent / "2026-11-18-overnight/claude-formal-vs-official-reference.json"
    benchmark = json.loads(benchmark_file.read_text(encoding="utf-8"))
    champion = next(row for row in benchmark["rounds"] if row["candidate"] == benchmark["candidate"])
    threshold = champion["score"]
    rows = []
    with (official / "contest-work/local-followup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.if_needed:
            expected = {(case, seed) for case in train for seed in SEEDS}
            for existing in output.glob("*-train.json"):
                card = json.loads(existing.read_text())
                actual = {(row["case"], row["seed"]) for row in card["cells"]}
                if (existing.name != "claude_r4-train.json" and card["image"] == settings["image"]
                        and actual == expected and len(card["cells"]) == len(expected)
                        and mean(row["score"] for row in card["cells"]) > threshold):
                    print(f"Local target already exceeded by {existing.name}", flush=True)
                    return
        for case, seed in cells:
            trial = run_trial(official, output, candidate.stem, case, str(seed), candidate,
                              lease_ttl_seconds=12 * 60 * 60)
            manifest = json.loads((trial / "DIAGNOSTIC_ONLY.json").read_text())
            if manifest["candidate_sha256"] != digest:
                raise ValueError(f"Candidate changed during measurement: {case}/{seed}")
            metrics, _, image = read_trial(trial, trial / "evaluation", case, str(seed))
            if image != settings["image"]:
                raise ValueError("Local trial image differs from bp controls")
            score = score_metrics(case, metrics)["combined_score"]
            rows.append({"case": case, "seed": seed, "score": score,
                         "wns_ns": metrics["final_global_wns_setup_ns"],
                         "tns_ns": metrics["final_global_tns_setup_ns"],
                         "receipt": str(trial / "evaluation/evaluation_result.json")})
            total = len(train) * len(SEEDS)
            remaining = total - len(rows)
            score_sum = sum(row["score"] for row in rows)
            seed_1002_scores = [row["score"] for row in rows if row["seed"] == 1002]
            result = {"scope": "local native training cells, common scoring", "candidate_sha256": digest,
                      "image": image, "benchmark": threshold, "cells": rows,
                      "three_design_seed_1002_score": mean(seed_1002_scores) if len(seed_1002_scores) == len(train) else None,
                      "case_means": {design: mean(row["score"] for row in rows if row["case"] == design)
                                     for design in train if sum(row["case"] == design for row in rows) == len(SEEDS)},
                      "cells_remaining": remaining,
                      "required_remaining_mean_to_tie": (threshold * total - score_sum) / remaining if remaining else None,
                      "maximum_possible_score": (score_sum + 100 * remaining) / total,
                      "full_score": None if remaining else score_sum / total}
            suffix = "-probe.json" if args.probe else "-train.json"
            if args.train_cell:
                suffix = f"-{case}-{seed}.json"
            target = output / (candidate.stem + suffix if args.candidate else "new-loss-full-train.json")
            pending = target.with_suffix(".tmp")
            pending.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            pending.replace(target)
            print(f"{len(rows)}/{total} {case}/{seed} {score:.4f}", flush=True)
            if args.stop_if_out and remaining and result["maximum_possible_score"] <= threshold:
                print(f"Upper bound {result['maximum_possible_score']:.4f} excludes target {threshold:.4f}", flush=True)
                return


if __name__ == "__main__":
    main()
