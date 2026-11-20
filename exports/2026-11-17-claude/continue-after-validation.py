"""Run public validation once the current formal training session finishes."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def log(message):
    print(time.strftime("%Y-%m-%d %H:%M:%S %Z"), message, flush=True)


def service_state(unit):
    return subprocess.check_output(
        ["systemctl", "show", unit, "-p", "ActiveState", "--value"], text=True
    ).strip()


def training_result(work):
    receipt = json.loads((work / "session-result.json").read_text(encoding="utf-8"))
    candidate = receipt.get("candidate_id", "")
    if (receipt.get("status") != "succeeded" or receipt.get("services_stopped") is not True
            or receipt.get("baseline") != "loss_decoder" or receipt.get("evaluation_mode") != "formal"
            or not re.fullmatch("[a-f0-9]{64}", candidate)):
        raise RuntimeError(f"Official training did not finish successfully in {work}")
    evaluations = receipt["budget"]["evaluations"]
    if not any(row["candidate_id"] == candidate and row["status"] == "succeeded" for row in evaluations):
        raise RuntimeError(f"Selected candidate has no complete training evaluation in {work}")
    return candidate, len(evaluations)


def wait_for_training(work, unit):
    log(f"Waiting for {unit} to finish its current training session.")
    while service_state(unit) in {"activating", "active", "reloading", "deactivating"}:
        time.sleep(30)
    return training_result(work)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit", required=True)
    parser.add_argument("--framework", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=True)
    for path in (args.framework, args.source, args.data, args.runtime, args.work):
        path.resolve(strict=True)

    def command(operation, work, *extra):
        return [
            sys.executable, "-B", "-m", "contest2", operation, "--baseline", "loss_decoder",
            "--source", str(args.source), "--data-root", str(args.data), "--runtime", str(args.runtime),
            "--work-root", str(work), *extra,
        ]

    candidate, used = wait_for_training(args.work, args.unit)
    if used != 10:
        raise RuntimeError(f"Original training used {used}/10 submissions. Public validation was not started.")
    log(f"Starting the six public validation cells for candidate {candidate}.")
    with (args.output / "public-validation.log").open("x", encoding="utf-8") as stream:
        subprocess.run(
            command("validate", args.work, "--candidate-id", candidate, "--retain-physical-files"),
            cwd=args.framework, stdout=stream, stderr=subprocess.STDOUT, check=True,
        )
    log(f"Public validation finished. Selected program: {args.work / 'candidates' / candidate / 'candidate.json'}")


if __name__ == "__main__":
    main()
