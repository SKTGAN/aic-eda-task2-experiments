"""Summarize measured local seed pairs using matched baselines and actual assignments."""
import argparse
import json
from pathlib import Path
from statistics import mean


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    folder = args.results.resolve()
    rows, hashes, images = [], set(), set()
    historical = {str(row["seed"]): row for row in json.loads(
        (folder / "historical-hard-negative-native.json").read_text(encoding="utf-8"))}
    for seed in ("1001", "1002", "1003"):
        path = folder / ("negative_second_moment-physical-" + seed + ".json")
        if not path.exists():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["formal_evaluation"] or record["case"] != "bp-ng45" or str(record["seed"]) != seed:
            raise ValueError("Wrong experimental scope")
        assignments = record["matched_assignment"]
        delta = record["change"]
        tns, wns = delta["final_global_tns_setup_ns"], delta["final_global_wns_setup_ns"]
        hashes.add(record["candidate_sha256"])
        images.add(record["image"])
        tns_name, wns_name = "final_global_tns_setup_ns", "final_global_wns_setup_ns"
        if historical[seed]["baseline_wns_tns"] != [record["initial"][wns_name], record["initial"][tns_name]]:
            raise ValueError("Historical and new trials use different measured controls")
        rows.append({"seed":seed, "instances":assignments["instance_count"],
                     "actual_changed":assignments["literal_changed"],
                     "changed_excluding_global_flip":assignments["after_best_global_flip"],
                     "initial_tns_ns":record["initial"][tns_name], "candidate_tns_ns":record["candidate"][tns_name],
                     "delta_tns_ns":tns, "delta_wns_ns":wns, "delta_score_points":delta["common_reference_score"],
                     "changed_and_tns_improved":assignments["after_best_global_flip"] > 0 and tns > 0,
                     "historical_hard_negative_delta_tns_ns":historical[seed]["tns_delta"],
                     "source":path.name})
    if len(hashes) != 1 or len(images) != 1:
        raise ValueError("Expected one fixed candidate and image")
    complete = len(rows) == 3
    result = {"scope":"local matched single-cell tests; not a formal matrix", "complete":complete,
              "candidate_sha256":next(iter(hashes)), "image":next(iter(images)), "seeds":rows,
              "changed_and_tns_improved_seeds":sum(r["changed_and_tns_improved"] for r in rows)}
    if complete:
        result["mean_delta_tns_ns"] = mean(r["delta_tns_ns"] for r in rows)
        result["mean_delta_score_points"] = mean(r["delta_score_points"] for r in rows)
    destination = folder / "new-loss-scorecard.json"
    pending = destination.with_suffix(".tmp")
    pending.write_text(json.dumps(result, indent=2)+"\n",encoding="utf-8")
    pending.replace(destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
