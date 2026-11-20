"""Run or resume the three offline Ariane comparisons in WSL."""

import argparse
from datetime import datetime
import fcntl
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import time

from compare_trials import read_json, read_trial


CASE = "ariane133-ng45"
BASELINE = "loss_decoder"
MEMORY_GIB = 6
HERE = Path(__file__).resolve().parent
PROGRAM = HERE / "hard_negative_margin.py"
EXPERIMENT = HERE.parent


def completed_trial(trials, seed, candidate_hash):
    expected = {
        "case": CASE, "seed": seed, "baseline": BASELINE,
        "memory_limit_gib": MEMORY_GIB, "candidate_sha256": candidate_hash,
        "formal": False,
    }
    result_path = "evaluation" if candidate_hash else "baseline/qualification"
    for manifest in sorted(trials.glob("*/DIAGNOSTIC_ONLY.json"), reverse=True):
        try:
            metadata = read_json(manifest)
            if any(metadata.get(key) != value for key, value in expected.items()):
                continue
            read_trial(manifest.parent, manifest.parent / result_path, CASE, seed)
        except (KeyError, OSError, StopIteration, ValueError):
            continue
        return manifest.parent
    return None


def run_trial(official, logs, seed, candidate_hash):
    trials = official / "contest-work" / "local-trials"
    variant = "hard-negative" if candidate_hash else "loss-decoder-initial"
    completed = completed_trial(trials, seed, candidate_hash)
    if completed is not None:
        print(f"Reusing verified {seed} {variant}: {completed}", flush=True)
        return completed

    command = [sys.executable, "-u", "-B", str(EXPERIMENT / "trial_baseline.py"),
               "--official", str(official), "--baseline", BASELINE, "--case", CASE,
               "--seed", seed, "--memory-gib", str(MEMORY_GIB)]
    if candidate_hash:
        command.extend(["--candidate", str(PROGRAM)])
    for attempt in range(1, 4):
        active = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
        if any(container.startswith("grt-") for container in active.splitlines()):
            raise SystemExit("A contest container is already running")

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        log = logs / f"{CASE}-{seed}-{variant}-resume-{stamp}.log"
        print(f"Running {seed} {variant}, attempt {attempt}: {log}", flush=True)
        with log.open("x", encoding="utf-8") as output:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=False)
        if result.returncode == 0:
            completed = completed_trial(trials, seed, candidate_hash)
            if completed is None:
                raise SystemExit(f"Completed trial could not be verified. See {log}")
            return completed

        failure = log.read_text(encoding="utf-8", errors="replace")
        if attempt == 3 or "UncertainExecution" in failure or "Insufficient available memory" not in failure:
            raise SystemExit(f"Local trial interrupted or failed. See {log}")
        print("Waiting for WSL to reclaim memory", flush=True)
        time.sleep(35)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    args = parser.parse_args()
    official = args.official.resolve(strict=True)
    logs = EXPERIMENT / "official" / "contest-work"
    candidate_hash = sha256(PROGRAM.read_text(encoding="utf-8").encode("utf-8")).hexdigest()

    with (official / "contest-work" / "ariane-validation.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("The Ariane batch is already running") from None
        for seed in ("1001", "1002", "1003"):
            initial = run_trial(official, logs, seed, None)
            candidate = run_trial(official, logs, seed, candidate_hash)
            report = subprocess.check_output(
                [sys.executable, "-B", str(HERE / "compare_trials.py"), str(initial), str(candidate)],
                text=True,
            )
            comparison = logs / f"{CASE}-{seed}-hard-negative-comparison.json"
            temporary = comparison.with_suffix(".json.tmp")
            temporary.write_text(report, encoding="utf-8")
            temporary.replace(comparison)
            print(f"Verified pair {seed}: {comparison}", flush=True)


if __name__ == "__main__":
    main()
