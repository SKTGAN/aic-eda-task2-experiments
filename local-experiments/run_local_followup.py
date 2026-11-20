"""Complete the outstanding layer-swap trials and a matched timing-weight test."""

import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from compare_trials import read_trial


ROOT = Path(__file__).resolve().parents[1]
MEMORY_GIB = 6
BASELINE = "loss_decoder"
REVISION_CANDIDATES = ROOT / "exports/2026-11-17-claude/revision/experiments/candidates"
FLIP = ROOT / "harness-feedback-template/experiments/flipped_layer_decoder.py"
TRIALS = [
    ("flip", "bp-ng45", "1002", FLIP),
    ("flip", "bp-ng45", "1003", FLIP),
    ("flip", "ariane133-ng45", "1002", FLIP),
    ("flip", "ariane133-ng45", "1003", FLIP),
    (
        "uniform-control", "bp_fe-ng45", "1003",
        REVISION_CANDIDATES / "uniform_weighted_positives_control.py",
    ),
    (
        "critical-positives", "bp_fe-ng45", "1003",
        REVISION_CANDIDATES / "criticality_weighted_positives.py",
    ),
]


def verified_trial(official, case, seed, program):
    digest = hashlib.sha256(program.read_text(encoding="utf-8").encode()).hexdigest() if program else None
    expected = {
        "baseline": BASELINE, "case": case, "seed": seed, "formal": False,
        "memory_limit_gib": MEMORY_GIB, "candidate_sha256": digest,
    }
    location = "evaluation" if program else "baseline/qualification"
    manifests = (official / "contest-work/local-trials").glob("*/DIAGNOSTIC_ONLY.json")
    for manifest in sorted(manifests, reverse=True):
        try:
            observed = json.loads(manifest.read_text(encoding="utf-8"))
            if any(observed.get(key) != value for key, value in expected.items()):
                continue
            read_trial(manifest.parent, manifest.parent / location, case, seed)
        except (KeyError, OSError, StopIteration, ValueError):
            continue
        return manifest.parent
    return None


def run_trial(official, output, tag, case, seed, program=None, *, lease_ttl_seconds=None):
    matched = verified_trial(official, case, seed, program)
    if matched:
        print(f"Verified existing {tag} {case}/{seed}: {matched.name}", flush=True)
        return matched

    command = [
        sys.executable, "-B", "-u", str(ROOT / "trial_baseline.py"),
        "--official", str(official), "--baseline", BASELINE,
        "--case", case, "--seed", seed, "--memory-gib", str(MEMORY_GIB),
    ]
    if program:
        command.extend(("--candidate", str(program)))
    if lease_ttl_seconds is not None:
        command.extend(("--lease-ttl-seconds", str(lease_ttl_seconds)))
    for attempt in (1, 2):
        running = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
        if any(name.startswith("grt-") for name in running.splitlines()):
            raise RuntimeError("An existing physical run is occupying the local Docker worker")
        log = output / f"{tag}-{case}-{seed}-{time.time_ns()}.log"
        print(f"Running {tag} {case}/{seed} → {log.name}", flush=True)
        with log.open("x", encoding="utf-8") as stream:
            status = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=False)
        if status.returncode == 0:
            matched = verified_trial(official, case, seed, program)
            if matched:
                return matched
            raise RuntimeError(f"No verified receipt for {tag} {case}/{seed}. See {log.name}.")
        errors = log.read_text(encoding="utf-8", errors="replace")
        if "Insufficient available memory" in errors and attempt == 1:
            print(f"Waiting for WSL memory before retrying {tag} {case}/{seed}", flush=True)
            time.sleep(30)
            continue
        raise RuntimeError(f"{tag} {case}/{seed} failed. See {log.name}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    official = args.official.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    unsuccessful = False
    with (official / "contest-work/local-followup.lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for method, case, seed, source in TRIALS:
            try:
                initial = run_trial(official, output, "initial", case, seed)
                candidate = run_trial(official, output, method, case, seed, source)
                comparison = subprocess.check_output(
                    [sys.executable, "-B", str(ROOT / "local-experiments/compare_trials.py"),
                     str(initial), str(candidate)],
                    text=True,
                )
                result = json.loads(comparison)
                destination = output / f"{method}-{case}-{seed}.json"
                pending = destination.with_suffix(".json.tmp")
                pending.write_text(comparison, encoding="utf-8")
                pending.replace(destination)
                print(f"{method} {case}/{seed} score change "
                      f"{result['change']['common_reference_score']:+.4f}", flush=True)
            except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
                unsuccessful = True
                print(error, flush=True)
    return int(unsuccessful)


if __name__ == "__main__":
    raise SystemExit(main())

