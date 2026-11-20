"""Measure paired training probes, then run an improved candidate on all nine cells."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
import subprocess
import sys


HERE = Path(__file__).resolve().parent
DRIVER = HERE.parent / "bp-boundary-20261118/measure_train_score.py"


def read_card(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--parent-card", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--cells", nargs="+", required=True)
    parser.add_argument("--screen-only", action="store_true", help="Record the paired probes for comparison with other candidates")
    args = parser.parse_args()
    parent = read_card(args.parent_card)
    baseline = {f"{r['case']}/{r['seed']}": r["score"] for r in parent["cells"]}
    if (len(parent["cells"]) != 9 or len(baseline) != 9 or parent["full_score"] is None
            or abs(mean(baseline.values()) - parent["full_score"]) > 1e-9):
        parser.error("Parent needs a complete nine-cell training score")
    if len(set(args.cells)) != len(args.cells) or not set(args.cells) <= baseline.keys():
        parser.error("Each probe must be a distinct training cell")
    candidate = args.candidate.resolve(strict=True)
    digest = hashlib.sha256(candidate.read_text(encoding="utf-8").encode()).hexdigest()
    output = args.parent_card.resolve().parent
    command = [sys.executable, "-B", "-u", str(DRIVER), "--official", str(args.official),
               "--output", str(output), "--candidate", str(candidate)]
    evidence = []
    for key in args.cells:
        subprocess.run(command + ["--train-cell", key], check=True)
        card = read_card(output / f"{candidate.stem}-{key.replace('/', '-')}.json")
        row, = card["cells"]
        if (card["image"] != parent["image"] or card["candidate_sha256"] != digest
                or f"{row['case']}/{row['seed']}" != key):
            raise ValueError(f"Probe did not match candidate, image or cell: {key}")
        evidence.append({"cell": key, "candidate_score": row["score"], "parent_score": baseline[key],
                         "change": row["score"] - baseline[key], "receipt": row["receipt"]})
    delta = mean(r["change"] for r in evidence)
    report = {"scope": "local paired training probes", "parent_sha256": parent["candidate_sha256"],
              "candidate_sha256": digest, "parent_full_score": parent["full_score"],
              "probes": evidence, "mean_probe_change": delta, "promoted": delta > 0 and not args.screen_only}
    target = output / f"{candidate.stem}-screen.json"
    pending = target.with_suffix(".json.tmp")
    pending.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    pending.replace(target)
    print(f"{candidate.stem}: {len(evidence)} probes, mean paired change {delta:+.6f}", flush=True)
    if report["promoted"]:
        subprocess.run(command, check=True)
        full = read_card(output / f"{candidate.stem}-train.json")
        keys = {f"{r['case']}/{r['seed']}" for r in full["cells"]}
        if (full["candidate_sha256"] != digest or keys != set(baseline)
                or full["image"] != parent["image"] or len(full["cells"]) != 9):
            raise ValueError("Unexpected full candidate matrix")
        print(f"Nine-cell change versus the parent: {full['full_score'] - parent['full_score']:+.6f}", flush=True)
    subprocess.run([sys.executable, "-B", str(HERE / "scoreboard.py")], check=True)


if __name__ == "__main__":
    main()
