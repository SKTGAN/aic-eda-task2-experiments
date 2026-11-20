"""Audit a frozen local candidate's run on the official six-cell public validation matrix."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from statistics import mean


PROJECT = Path(__file__).resolve().parents[2]
CLAUDE = PROJECT / "exports/2026-11-19-claude-expert-audit/runs/15332-claude-original-34/public-validation.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same_score(left, right):
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-10)


def terminal_cell(folder, row, cell, candidate, capsule, image, score_metrics):
    result = folder / "result"
    control = folder / "container"
    request = read(control / "request.json")
    require(request["candidate"] == str(candidate) and request["output"] == str(result),
            f"Candidate or result path differs at {folder}")
    options = request["options"]
    require(all(options[k] == cell[k] for k in ("base_config", "baseline_run", "reference_run"))
            and options["seed_schedule"] == cell["seeds"], f"Native cell inputs differ at {folder}")
    snapshot = result / "candidate_snapshot.json"
    if row["status"] == "succeeded" or snapshot.exists():
        require(read(snapshot) == capsule, f"Native candidate snapshot differs at {folder}")
    execution = control / "execution"
    container_prefix = "grt-" + read(control / "lease.json")["job"][:32] + "-"
    phases = ["frontend", "backend"] if row["status"] == "succeeded" or (execution / "backend").exists() else ["frontend"]
    for phase in phases:
        terminal = read(execution / phase / "terminal.json")
        require(image in read(execution / phase / "command.json") and terminal["container"] == container_prefix + phase
                and type(terminal["exit_code"]) is int,
                f"Image or terminal receipt differs at {folder}/{phase}")
        if row["status"] == "succeeded":
            require(terminal["exit_code"] == 0, f"Failed native {phase} at {folder}")

    native = read(result / "evaluation_result.json")["metrics"]
    if row["status"] == "penalized":
        evidence = row["physical_failure_evidence"]
        require(row["score"] == -100 and row["valid"] is False and bool(evidence) and not native["runs_successfully"],
                f"Unconfirmed physical penalty at {folder}")
        for relative, digest in evidence.items():
            witness = (folder / relative).resolve(strict=True)
            require(folder in witness.parents and hashlib.sha256(witness.read_bytes()).hexdigest() == digest,
                    f"Failure evidence differs at {witness}")
        return {"status": "penalized", "score": -100.0, "reason": row.get("error_message")}
    verified = score_metrics(row["case"], native)
    require(row["valid"] is True and same_score(verified["combined_score"], row["score"])
            and same_score(verified["raw_score"], row["raw_score"]), f"Native score differs at {folder}")
    return {"status": "succeeded", "score": row["score"], "raw_score": verified["raw_score"],
            "wns_ns": native["final_global_wns_setup_ns"], "tns_ns": native["final_global_tns_setup_ns"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("work", "official", "training-card", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    work, official = args.work.resolve(strict=True), args.official.resolve(strict=True)
    source = official / "contest-source"
    framework = source / "AgenticBench"
    sys.path.insert(0, str(framework))
    from contest2.halo_policy import validate_matrix_halos
    from contest2.sampling import validate_public_matrix
    from contest2.scoring import PUBLIC_SPLITS, SEEDS, complete_score, reference_table, score_metrics, validate_scoring_references
    from grt_bench.common import sha, write
    from local_bench.matrix import LocalEvaluationMatrix
    from local_bench.model import load_task
    from local_bench.program_bridge import materialize_program

    data = official / "contest-data/task2"
    manifest = data / "loss_decoder/validation/qualified_matrix.json"
    spec = load_task(framework / "local_tasks/tp_gnn_loss_decoder_timing")
    matrix = LocalEvaluationMatrix(manifest, spec)
    validate_public_matrix(matrix, "loss_decoder", "validation")
    validate_scoring_references(matrix, "loss_decoder")
    validate_matrix_halos(matrix)
    meta = read(work / "DIAGNOSTIC_ONLY.json")
    training = read(args.training_card)
    image = read(data / "runtime.json")["image"]
    candidate = work / "candidate"
    program = (candidate / "program.py").read_text(encoding="utf-8")
    digest = hashlib.sha256(program.encode()).hexdigest()
    require(meta["formal"] is False and meta["baseline"] == "loss_decoder" and meta["split"] == "validation"
            and Path(meta["matrix"]).resolve() == manifest and meta["candidate_sha256"] == digest
            and training["candidate_sha256"] == digest and training["image"] == image,
            "Validation manifest, image or training candidate differs")
    train = training["cells"]
    require(len(train) == 9 and {(r["case"], r["seed"]) for r in train} ==
            {(c, s) for c in PUBLIC_SPLITS["train"] for s in SEEDS}
            and same_score(mean(r["score"] for r in train), training["full_score"]), "Incomplete training score")
    capsule = materialize_program(spec, program, source)
    require(capsule == read(candidate / "candidate.json"), "Frozen capsule differs from its source")
    root = work / "validate" / digest
    plan = read(root / "matrix.json")
    require(plan["matrix_sha256"] == matrix.identity and plan["cells"] == matrix.cells
            and plan["planned_native_cells"] == 6 and plan["qualification"] is False, "Matrix plan differs")

    prior = next(iter(read(CLAUDE).values()))
    prior_rows = {(r["case"], r["seed"]): r["score"] for r in prior["matrix"]["cells"]}
    refs = reference_table()["cases"]
    result_path = root / "evaluation_result.json"
    # A cell finishing during a progress export is included on the next invocation.
    original = read(result_path) if result_path.exists() else None
    rows, native_rows = [], []
    for cell in matrix.cells:
        case, seed = cell["case"], cell["seed"]
        initial = refs[case]["measurements"]["loss_decoder"][seed]
        reference = {"runs_successfully": 1, "sta_graph_complete": 1, "timing_evaluation_boundary": "post-opt-pre-cts",
                     "combined_score": 0, "final_global_wns_setup_ns": initial["wns_ns"], "final_global_tns_setup_ns": initial["tns_ns"]}
        row = {"case": case, "seed": seed, "status": "pending", "score": None,
               "published_initial_wns_ns": initial["wns_ns"], "published_initial_tns_ns": initial["tns_ns"],
               "published_initial_score": score_metrics(case, reference)["combined_score"],
               "historical_claude_4090_score": prior_rows[case, seed]}
        folder = root / "cells" / case / seed
        if (folder / "cell.json").exists():
            receipt = read(folder / "cell.json")
            require((receipt["case"], receipt["seed"]) == (case, seed), f"Unexpected cell at {folder}")
            native_rows.append(receipt)
            if receipt["status"] in ("succeeded", "penalized"):
                row.update(terminal_cell(folder, receipt, cell, candidate, capsule, image, score_metrics))
            else:
                row.update(status=receipt["status"], reason=receipt.get("error_message"))
        rows.append(row)

    scores = [r["score"] for r in rows if r["score"] is not None]
    total = None
    if original is not None:
        metrics = original["metrics"]
        require(metrics["matrix"]["cells"] == native_rows, "Final matrix differs from native cell receipts")
        if complete_score(metrics, matrix):
            require(len(scores) == 6 and same_score(mean(scores), metrics["combined_score"]), "Validation score differs")
            total = metrics["combined_score"]
        elif metrics["matrix"].get("complete") or "combined_score" in metrics:
            raise ValueError("Invalid complete matrix")
    per_case = {}
    for case in matrix.cases:
        values = [r["score"] for r in rows if r["case"] == case and r["score"] is not None]
        per_case[case] = mean(values) if len(values) == len(SEEDS) else None
    report = {"scope": "frozen local candidate on the official public validation matrix",
              "candidate_sha256": digest, "image": image, "matrix_sha256": matrix.identity,
              "complete": total is not None, "scored_cells": len(scores), "cells": rows,
              "case_means": per_case, "validation_score": total, "training_score": training["full_score"],
              "public_five_case_score": None if total is None else (3 * training["full_score"] + 2 * total) / 5,
              "published_initial_validation_score": mean(r["published_initial_score"] for r in rows),
              "historical_claude_4090_validation_score": prior["metrics"]["combined_score"],
              "native_result": str(result_path)}
    output = args.output.resolve()
    require(all(output != parent and parent not in output.parents for parent in (official, work)),
            "Select an export directory outside the original task and work directories")
    if total is not None:
        archive = output / "evaluation_result.json"
        write(archive, original, replace=True)
        require(sha(archive) == sha(result_path), "Archived official matrix differs from the source")
        report["native_result_sha256"] = sha(archive)
    write(output / "public-validation.json", report, replace=True)
    print(f"{len(scores)}/6 scored, validation={total}, public_five={report['public_five_case_score']}")


if __name__ == "__main__":
    main()
