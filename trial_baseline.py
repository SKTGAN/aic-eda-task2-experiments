"""Run a training cell or the full public validation matrix as a local diagnostic."""

import argparse
from contextlib import contextmanager
from datetime import datetime
from functools import partial
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-gib", type=int, default=6)
    parser.add_argument("--lease-ttl-seconds", type=int, help="Private local queue lease duration across host suspend")
    parser.add_argument("--official", type=Path, default=Path(__file__).resolve().parent / "official")
    parser.add_argument("--candidate", type=Path, help="Run an offline candidate against the packed reference")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--public-validation", action="store_true", help="Evaluate the frozen candidate on the entire published validation matrix")
    mode.add_argument("--development-validation-cell", action="store_true", help="Use a single public validation cell as local development data")
    mode.add_argument("--development-training-cell", action="store_true", help="Measure a single published training cell with host-confirmed physical penalties")
    parser.add_argument("--expected-sha256", help="Require this SHA-256 digest of the candidate source before dispatch")
    parser.add_argument("--baseline", choices=("binary_loss", "loss_decoder"), default="binary_loss")
    parser.add_argument("--case", default="bp_fe-ng45")
    parser.add_argument("--seed", default="1003")
    args = parser.parse_args()
    if args.memory_gib < 1:
        parser.error("--memory-gib must be positive")
    if args.lease_ttl_seconds is not None and args.lease_ttl_seconds < 1:
        parser.error("--lease-ttl-seconds must be positive")
    use_validation_inputs = args.public_validation or args.development_validation_cell
    checked_panel = use_validation_inputs or args.development_training_cell
    if (checked_panel or args.expected_sha256) and not args.candidate:
        parser.error("A scored panel and --expected-sha256 require --candidate")

    official = args.official.resolve(strict=True)
    source = official / "contest-source"
    framework = source / "AgenticBench"
    data = official / "contest-data" / "task2"
    work = official / "contest-work" / "local-trials" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    sys.path.insert(0, str(framework))

    from contest2.runner import _runtime, TASK_IDS
    from grt_bench.common import write
    from local_bench.matrix import LocalEvaluationMatrix, qualify_matrix
    from local_bench import matrix_docker
    from local_bench.model import load_task
    from local_bench.program_bridge import materialize_program
    from local_bench.verifier import verify_candidate

    admit = matrix_docker.admission

    def wait_for_admission(folder, resources, gpus):
        # The frontend can exit before WSL has reclaimed its memory.
        # Retry the same check before launching either diagnostic phase.
        deadline = time.monotonic() + 60
        announced = False
        while True:
            try:
                return admit(folder, resources, gpus)
            except RuntimeError as error:
                if str(error) != "Insufficient available memory" or time.monotonic() >= deadline:
                    raise
                if not announced:
                    print("Waiting for WSL memory before starting the next container", flush=True)
                    announced = True
                time.sleep(3)

    class TrialTransport(matrix_docker.DockerMatrixTransport):
        @contextmanager
        def lease(self, folder, resources):
            with super().lease(folder, {**resources, "memory_gb": args.memory_gib}) as claim:
                yield claim

        def run_phased(self, request, run, image, resources, claim, mounts):
            return super().run_phased(
                request, run, image, {**resources, "memory_gb": args.memory_gib}, claim, mounts
            )

    baseline = args.baseline
    case, seed = args.case, args.seed
    task_dir = framework / "local_tasks" / TASK_IDS[baseline]
    spec = load_task(task_dir)
    split = "validation" if use_validation_inputs else "train"
    published_matrix = data / baseline / split / "qualified_matrix.json"
    if checked_panel:
        from contest2.halo_policy import validate_matrix_halos
        from contest2.sampling import validate_public_matrix
        from contest2.scoring import validate_scoring_references
        matrix_path = published_matrix
        public_matrix = LocalEvaluationMatrix(matrix_path, spec)
        validate_matrix_halos(public_matrix)
        validate_public_matrix(public_matrix, baseline, split)
        validate_scoring_references(public_matrix, baseline)
    if not args.public_validation:
        matrix = json.loads(published_matrix.read_text())
        cell = next((row for row in matrix["cells"] if (row["case"], row["seed"]) == (case, seed)), None)
        if cell is None:
            parser.error(f"{case} / {seed} is not a published {split} cell")
        for field in ("base_config", "baseline_run", "reference_run"):
            cell[field] = str((published_matrix.parent / cell[field]).resolve(strict=True))
        matrix.update(cases=[case], seeds=[row for row in matrix["seeds"] if row["id"] == seed], cells=[cell])
        matrix_path = work / "single-cell.json"
        write(matrix_path, matrix)
    candidate_hash = None
    if args.candidate:
        candidate_source = args.candidate.read_text(encoding="utf-8")
        candidate_hash = hashlib.sha256(candidate_source.encode("utf-8")).hexdigest()
        if args.expected_sha256 and candidate_hash != args.expected_sha256:
            parser.error("The candidate source differs from the requested frozen SHA-256")
        payload = materialize_program(spec, candidate_source, source)
        verify_candidate(spec, payload, source)
        candidate_dir = work / "candidate"
        write(candidate_dir / "candidate.json", payload)
        (candidate_dir / "program.py").write_text(candidate_source, encoding="utf-8")
    write(work / "DIAGNOSTIC_ONLY.json", {
        "formal": False, "baseline": baseline, "split": split,
        "public_validation_used_for_development": args.development_validation_cell,
        "case": None if args.public_validation else case, "seed": None if args.public_validation else seed,
        "memory_limit_gib": args.memory_gib, "matrix": str(published_matrix),
        "candidate_sha256": candidate_hash,
        "private_queue_lease_ttl_seconds": args.lease_ttl_seconds,
    })
    panel = "public validation (six cells)" if args.public_validation else f"{case} / seed {seed}"
    print(f"Running {baseline} / {panel} with {args.memory_gib} GiB")
    print(f"Artifacts: {work}", flush=True)

    _, runtime = _runtime(data / "runtime.json", work_root=work, private_queue=True)
    transport = TrialTransport(queue=runtime["queue"], host=runtime["host"], image=runtime["image"])
    if args.lease_ttl_seconds is not None:
        transport.queue.claim = partial(transport.queue.claim, ttl=args.lease_ttl_seconds)
        transport.queue.heartbeat = partial(transport.queue.heartbeat, ttl=args.lease_ttl_seconds)
    if args.public_validation:
        from contest2.storage import TrainingStorageTransport
        transport = TrainingStorageTransport(transport, work / "validate", retain_physical_files=True)
    elif checked_panel:
        from contest2.storage import TrainingStorageTransport
        transport = TrainingStorageTransport(transport, work, retain_physical_files=True)
    with patch.object(matrix_docker, "admission", wait_for_admission):
        if args.candidate:
            result_dir = work / "validate" / candidate_hash if args.public_validation else work / "evaluation"
            evaluation_matrix = public_matrix if args.public_validation else LocalEvaluationMatrix(matrix_path, spec)
            result = evaluation_matrix.evaluate(
                candidate_dir, source, result_dir, transport=transport, workers=1, timeout_seconds=None,
            )
        else:
            result_dir = work / "baseline" / "qualification"
            result = qualify_matrix(
                matrix_path, task_dir, source, work / "baseline",
                transport=transport, workers=1, timeout_seconds=None,
            )
    print(f"Result: {result_dir / 'evaluation_result.json'}", flush=True)
    if checked_panel:
        from contest2.scoring import complete_score
        complete = complete_score(result.metrics, evaluation_matrix)
        print(json.dumps({"complete": complete, "score": result.metrics.get("combined_score"),
                          "cells": [(r["case"], r["seed"], r["status"], r.get("score"))
                                    for r in result.metrics["matrix"]["cells"]]}, indent=2))
        return 0 if complete else 1
    row = result.metrics["matrix"]["cells"][0]
    print(json.dumps({key: row[key] for key in ("status", "metrics", "error_message") if key in row}, indent=2))
    return 0 if result.metrics["runs_successfully"] == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
