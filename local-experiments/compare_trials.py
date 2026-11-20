"""Compare a local initial-algorithm trial and candidate on the same cell."""

import argparse
import json
from pathlib import Path
import sys


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_trial(trial, result_dir, case, seed):
    matrix = read_json(result_dir / "evaluation_result.json")["metrics"]["matrix"]
    if matrix["expected_cells"] != 1 or matrix["succeeded_cells"] != 1:
        raise ValueError(f"Expected one successful cell in {trial}")
    row = matrix["cells"][0]
    if (row["case"], row["seed"]) != (case, seed) or row["status"] != "succeeded":
        raise ValueError(f"Unexpected cell in {trial}")
    cell = result_dir / "cells" / case / seed
    execution = cell / "container" / "execution"
    receipts = [read_json(execution / phase / "terminal.json") for phase in ("frontend", "backend")]
    if any(receipt["exit_code"] != 0 for receipt in receipts):
        raise ValueError(f"Container failure in {trial}")
    settings = read_json(execution / "frontend" / "command.json")
    image = next(argument for argument in settings if argument.startswith("sha256:"))
    return row["metrics"], sum(receipt["wall_seconds"] for receipt in receipts), image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("initial_trial", type=Path)
    parser.add_argument("candidate_trial", type=Path)
    args = parser.parse_args()
    initial, candidate = (path.resolve(strict=True) for path in (args.initial_trial, args.candidate_trial))
    initial_meta, candidate_meta = (read_json(path / "DIAGNOSTIC_ONLY.json") for path in (initial, candidate))
    if (
        initial.parent != candidate.parent
        or initial_meta["formal"] is not False or candidate_meta["formal"] is not False
        or initial_meta.get("candidate_sha256") is not None or not candidate_meta.get("candidate_sha256")
        or read_json(initial / "single-cell.json") != read_json(candidate / "single-cell.json")
        or initial_meta["memory_limit_gib"] != candidate_meta["memory_limit_gib"]
    ):
        raise ValueError("Supply paired initial and candidate trials with the same local settings")

    case, seed = initial_meta["case"], initial_meta["seed"]
    baseline_dir = initial / "baseline" / "qualification"
    candidate_dir = candidate / "evaluation"
    before, before_seconds, before_image = read_trial(initial, baseline_dir, case, seed)
    after, after_seconds, after_image = read_trial(candidate, candidate_dir, case, seed)
    if before_image != after_image:
        raise ValueError("Trial images differ")

    source = initial.parents[2] / "contest-source" / "AgenticBench"
    sys.path.insert(0, str(source))
    from contest2.scoring import score_metrics

    timing_and_cut = (
        "final_global_wns_setup_ns",
        "final_global_tns_setup_ns",
        "cut_net_count",
        "timing_weighted_cut",
    )
    if initial_meta["baseline"] == "binary_loss":
        timing_and_cut += (
            "binary_raw_top_area_ratio",
            "binary_final_top_area_ratio",
            "binary_closure_moved_area_fraction",
        )
    else:
        timing_and_cut += (
            "tp_gnn_positive_pair_cosine_median",
            "tp_gnn_negative_pair_cosine_median",
            "tp_gnn_embedding_total_variance",
            "tp_gnn_repair_moved_area_fraction",
        )
    metrics = {}
    for name, measured in (("initial", before), ("candidate", after)):
        metrics[name] = {key: measured[key] for key in timing_and_cut}
        metrics[name]["common_reference_score"] = score_metrics(case, measured)["combined_score"]

    report = {
        "formal_evaluation": False, "baseline": initial_meta["baseline"],
        "case": case, "seed": int(seed), "image": before_image,
        "memory_limit_gib": initial_meta["memory_limit_gib"],
        "candidate_sha256": candidate_meta["candidate_sha256"],
        **metrics,
        "change": {key: value - metrics["initial"][key] for key, value in metrics["candidate"].items()},
        "container_wall_seconds": {
            "initial": round(before_seconds, 2),
            "candidate": round(after_seconds, 2),
        },
        "initial_result": str(baseline_dir / "evaluation_result.json"),
        "candidate_result": str(candidate_dir / "evaluation_result.json"),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
