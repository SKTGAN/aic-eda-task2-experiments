"""Measure a fixed local program on selected cells from one public split."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean

from export_public_validation import PROJECT, read, require, terminal_cell


def source_digest(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def checked_cell(work, cell, spec, source, capsule, image):
    from contest2.scoring import complete_score, score_metrics
    from local_bench.matrix import LocalEvaluationMatrix

    case, seed = cell["case"], cell["seed"]
    candidate = work / "candidate"
    require((candidate / "program.py").read_text(encoding="utf-8") == source
            and read(candidate / "candidate.json") == capsule, f"Candidate differs at {work}")
    matrix = LocalEvaluationMatrix(work / "single-cell.json", spec)
    require(matrix.cells == [cell], f"Development input differs at {work}")
    root = work / "evaluation"
    plan = read(root / "matrix.json")
    require(plan["matrix_sha256"] == matrix.identity and plan["cells"] == [cell]
            and plan["planned_native_cells"] == 1 and plan["qualification"] is False,
            f"Invalid native matrix plan at {work}")
    folder = root / "cells" / case / seed
    receipt = read(folder / "cell.json")
    metrics = read(root / "evaluation_result.json")["metrics"]
    require(complete_score(metrics, matrix) and metrics["matrix"]["cells"] == [receipt],
            f"Incomplete native matrix at {work}: {receipt.get('status')}, {receipt.get('error_message', '')}")
    verified = terminal_cell(folder, receipt, cell, candidate, capsule, image, score_metrics)
    return dict(case=case, seed=seed, native_result=str(root / "evaluation_result.json"),
                matrix_sha256=matrix.identity, **verified)


def matching_work(trials, expected):
    for marker in sorted(trials.glob("*/DIAGNOSTIC_ONLY.json"), reverse=True):
        try:
            meta = read(marker)
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        # Early training runs stored the published manifest path before adding the split flags.
        if expected.get("split") == "train" and meta.get("matrix") == expected["matrix"]:
            meta.setdefault("split", "train")
            meta.setdefault("public_validation_used_for_development", False)
        if all(meta.get(k) == v for k, v in expected.items()):
            yield marker.parent


def run_native(official, candidate, digest, cell, log, split):
    names = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
    if any(name.startswith("grt-") for name in names.splitlines()):
        raise RuntimeError("Another native physical job occupies the worker")
    mode = "--development-training-cell" if split == "train" else "--development-validation-cell"
    command = [sys.executable, "-B", "-u", str(PROJECT / "trial_baseline.py"), "--official", str(official),
               mode, "--candidate", str(candidate), "--expected-sha256", digest,
               "--baseline", "loss_decoder", "--case", cell["case"], "--seed", cell["seed"],
               "--memory-gib", "6", "--lease-ttl-seconds", "43200"]
    print(f"Running {cell['case']}/{cell['seed']} -> {log.name}", flush=True)
    with log.open("x", encoding="utf-8") as stream:
        status = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    if status:
        raise RuntimeError(f"Native process exited with {status}; see {log}")
    lines = log.read_text(encoding="utf-8").splitlines()
    work, = [Path(line.removeprefix("Artifacts: ")) for line in lines if line.startswith("Artifacts: ")]
    return work.resolve(strict=True)


def main():
    import fcntl

    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("official", "candidate", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    parser.add_argument("--cells", nargs="+", required=True, metavar="CASE/SEED")
    parser.add_argument("--split", choices=("train", "validation"), default="validation")
    args = parser.parse_args()
    official = args.official.resolve(strict=True)
    candidate = args.candidate.resolve(strict=True)
    source = candidate.read_text(encoding="utf-8")
    digest = source_digest(source)
    tree = official / "contest-source"
    framework = tree / "AgenticBench"
    sys.path.insert(0, str(framework))
    from contest2.halo_policy import validate_matrix_halos
    from contest2.sampling import validate_public_matrix
    from contest2.scoring import reference_table, score_metrics, validate_scoring_references
    from local_bench.matrix import LocalEvaluationMatrix
    from local_bench.model import load_task
    from local_bench.program_bridge import materialize_program
    from local_bench.verifier import verify_candidate

    manifest = official / "contest-data/task2/loss_decoder" / args.split / "qualified_matrix.json"
    spec = load_task(framework / "local_tasks/tp_gnn_loss_decoder_timing")
    public = LocalEvaluationMatrix(manifest, spec)
    validate_public_matrix(public, "loss_decoder", args.split)
    validate_matrix_halos(public)
    validate_scoring_references(public, "loss_decoder")
    references = reference_table()["cases"]
    known = {f"{r['case']}/{r['seed']}": r for r in public.cells}
    if not set(args.cells) <= known.keys() or len(set(args.cells)) != len(args.cells):
        parser.error("Specify unique cells from the selected published split")
    capsule = materialize_program(spec, source, tree)
    verify_candidate(spec, capsule, tree)
    image = read(official / "contest-data/task2/runtime.json")["image"]
    output = args.output.resolve()
    require(output != official and official not in output.parents, "Select an export directory outside the official task")
    output.mkdir(parents=True, exist_ok=True)
    panel_id = source_digest("\n".join(sorted(args.cells)))[:12]
    tag = f"{candidate.stem}-{digest[:12]}-{panel_id}"
    card = output / (tag + ".json")
    trials = official / "contest-work/local-trials"
    rows = []
    report = {"scope": f"local development on public {args.split} inputs", "split": args.split,
              "candidate_sha256": digest, "image": image, "published_matrix_sha256": public.identity,
              "requested": args.cells, "cells": rows, "complete": False, "panel_score": None}

    def save():
        pending = card.with_suffix(".json.tmp")
        pending.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        pending.replace(card)

    with (trials.parent / "local-followup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        save()
        for key in args.cells:
            cell = known[key]
            expected = {"case": cell["case"], "seed": cell["seed"], "formal": False, "split": args.split,
                        "baseline": "loss_decoder", "public_validation_used_for_development": args.split == "validation",
                        "memory_limit_gib": 6, "candidate_sha256": digest, "matrix": str(manifest)}
            log = output / f"{tag}-{key.replace('/', '-')}-{time.time_ns()}.log"
            try:
                result = None
                for work in matching_work(trials, expected):
                    try:
                        result = checked_cell(work, cell, spec, source, capsule, image)
                        break
                    except (OSError, ValueError, KeyError) as error:
                        print(f"Ignored unverifiable previous run {work.name}: {error}", flush=True)
                if result is None:
                    work = run_native(official, candidate, digest, cell, log, args.split)
                    require(work.parent == trials, f"Unexpected native work directory: {work}")
                    meta = read(work / "DIAGNOSTIC_ONLY.json")
                    require(all(meta.get(k) == v for k, v in expected.items()), f"Unexpected metadata: {work}")
                    result = checked_cell(work, cell, spec, source, capsule, image)
                initial = references[cell["case"]]["measurements"]["loss_decoder"][cell["seed"]]
                baseline_metrics = {"runs_successfully": 1, "sta_graph_complete": 1,
                                    "timing_evaluation_boundary": "post-opt-pre-cts", "combined_score": 0,
                                    "final_global_wns_setup_ns": initial["wns_ns"], "final_global_tns_setup_ns": initial["tns_ns"]}
                initial_score = score_metrics(cell["case"], baseline_metrics)["combined_score"]
                result.update(published_initial_wns_ns=initial["wns_ns"], published_initial_tns_ns=initial["tns_ns"],
                              published_initial_score=initial_score, delta_from_published_initial=result["score"] - initial_score)
                rows.append(result)
            except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as error:
                report["failure"] = {"cell": key, "message": str(error), "log": str(log) if log.exists() else None}
                save()
                raise
            save()
            print(f"{len(rows)}/{len(args.cells)} {key} {result['status']} {result['score']:.6f}", flush=True)
        cases = sorted({r["case"] for r in rows})
        case_means = {case: mean(r["score"] for r in rows if r["case"] == case) for case in cases}
        report.update(complete=True, case_means=case_means, panel_score=mean(case_means.values()))
        save()
    print(f"Panel mean {report['panel_score']:.6f}: {card}", flush=True)


if __name__ == "__main__":
    main()
