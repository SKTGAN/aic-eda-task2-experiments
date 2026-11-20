"""Screen fixed candidates on matched cells, then verify the nine-cell threshold."""
import argparse
import json
from pathlib import Path
from statistics import mean
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("candidates", nargs="+", type=Path)
    args = parser.parse_args()
    driver = Path(__file__).resolve().parents[1] / "bp-boundary-20261118/measure_train_score.py"
    command = [sys.executable, "-B", "-u", str(driver), "--official", str(args.official),
               "--output", str(args.output), "--stop-if-out"]
    candidates = [path.resolve(strict=True) for path in args.candidates]
    ranking = []
    for source in candidates:
        subprocess.run(command + ["--candidate", str(source), "--probe"], check=True)
        card = json.loads((args.output / (source.stem + "-probe.json")).read_text())
        ranking.append((mean(row["score"] for row in card["cells"]), source))
    for _, source in sorted(ranking, key=lambda item: item[0], reverse=True):
        subprocess.run(command + ["--candidate", str(source)], check=True)
        card = json.loads((args.output / (source.stem + "-train.json")).read_text())
        if card["full_score"] is not None and card["full_score"] > card["benchmark"]:
            print(f'Nine-cell score {card["full_score"]:.6f} exceeds {card["benchmark"]:.6f}: {source}', flush=True)
            break


if __name__ == "__main__":
    main()
