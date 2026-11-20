"""Run a development-only three-case matrix on three fixed GPU slots."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stdout
import fcntl
import hashlib
from itertools import cycle
import json
import math
import os
from pathlib import Path
import re
import secrets
from statistics import mean
import subprocess
import sys
import tempfile
import time


CASES = ("bp_fe-ng45", "bp-ng45", "ariane133-ng45")
SEEDS = ("1001", "1002", "1003")
ROOT = Path(__file__).resolve().parent


def atomic(path, value):
    temporary = path.with_suffix(".pending")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def framework(official):
    source = official / "contest-source"
    bench = source / "AgenticBench"
    sys.path.insert(0, str(bench))
    return source, bench, official / "contest-data" / "task2"


def full_matrix(bench, data):
    from contest2.sampling import validate_public_matrix
    from contest2.scoring import validate_scoring_references
    from local_bench.matrix import LocalEvaluationMatrix
    from local_bench.model import load_task

    spec = load_task(bench / "local_tasks" / "tp_gnn_loss_decoder_timing")
    matrix = LocalEvaluationMatrix(data / "loss_decoder" / "train" / "qualified_matrix.json", spec)
    validate_public_matrix(matrix, "loss_decoder", "train")
    validate_scoring_references(matrix, "loss_decoder")
    return matrix


@contextmanager
def host_slot(directory, limit):
    """Hold one host-wide reservation until the native CPU backend finishes."""
    directory.mkdir(parents=True, exist_ok=True)
    while True:
        for index in range(limit):
            with (directory / f"{index}.lock").open("a") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                yield
                return
        time.sleep(0.25)


def assigned_cells(cases, request):
    if not isinstance(request, dict) or set(request) not in (
            {"run", "request", "program", "seeds"}, {"run", "request", "program", "cells"}):
        raise ValueError("Unexpected request fields")
    panel = request.get("cells")
    if "seeds" in request and len(cases) == 1:
        panel = {cases[0]: request["seeds"]}
    if not isinstance(panel, dict) or not panel or set(panel) - set(cases):
        raise ValueError("Request uses a case outside the fixed worker allocation")
    for seeds in panel.values():
        if (not isinstance(seeds, list) or not seeds or any(seed not in SEEDS for seed in seeds)
                or len(set(seeds)) != len(seeds)):
            raise ValueError("Invalid training seeds")
    return panel


def physical_case(official, cases, gpu, request, workers=1, host_slots=1, memory_gib=24):
    source, bench, data = framework(official)
    from contest2.runtime_images import install, records
    from contest2.scoring import complete_score
    from contest2.storage import TrainingStorageTransport
    from grt_bench.queue import Queue
    from local_bench.matrix import LocalEvaluationMatrix
    from local_bench.matrix_docker import DockerMatrixTransport
    from local_tasks.tp_gnn_local_task_definitions import DECODER_TASK, materialize_loss_decoder, validate_program

    allocated = assigned_cells(cases, request)
    for key in ("run", "request"):
        if not isinstance(request[key], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,96}", request[key]):
            raise ValueError("Invalid development job ID")
    program = validate_program(request["program"], DECODER_TASK)
    program_sha = hashlib.sha256(program.encode()).hexdigest()
    slot = ROOT / "workers" / ("+".join(cases) + "-gpu" + str(gpu))
    slot.mkdir(parents=True, exist_ok=True)
    with (ROOT / ("gpu-" + str(gpu) + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        job = slot / request["run"] / request["request"]
        reply = job / "reply.json"
        if reply.is_file():
            prior = json.loads(reply.read_text())
            previous = prior.get("assigned") or {prior["case"]: prior["seeds"]}
            if prior["program_sha"] != program_sha or previous != allocated:
                raise ValueError("Job ID already bound to a different program or seed schedule")
            return prior
        if job.exists():
            raise RuntimeError("Existing unfinished job requires inspection before another attempt")
        job.mkdir(parents=True)
        matrix = full_matrix(bench, data)
        seeds = {seed for group in allocated.values() for seed in group}
        config = {"schema_version": 2, "task": DECODER_TASK, "cases": list(allocated),
                  "case_seeds": allocated, "seeds": [row for row in matrix.seeds if row["id"] in seeds],
                  "cells": [{key: cell[key] for key in ("case", "seed", "base_config", "baseline_run", "reference_run")}
                            for cell in matrix.cells if cell["seed"] in allocated.get(cell["case"], ())]}
        atomic(job / "plan.json", config)
        panel = LocalEvaluationMatrix(job / "plan.json", matrix.spec)
        image = next(iter(records()))
        install(image, job)
        queue_path = job / "queue.sqlite"
        Queue(queue_path).register_host("gpu-slot", {"cpu": 4 * workers, "memory_gb": memory_gib * workers,
                                                     "storage_gb": 20 * workers,
                                                     "gpus": [str(gpu)], "build_slots": 0})

        class HostBoundTransport(DockerMatrixTransport):
            @contextmanager
            def lease(self, folder, resources):
                with host_slot(ROOT / "host-slots", host_slots):
                    with super().lease(folder, {**resources, "memory_gb": memory_gib}) as claim:
                        yield claim

            def run_phased(self, request, run, image, resources, claim, mounts):
                return super().run_phased(request, run, image, {**resources, "memory_gb": memory_gib}, claim, mounts)

        transport = HostBoundTransport(queue=queue_path, host="gpu-slot", image=image, admission_timeout=None)
        candidate = job / "candidate"
        candidate.mkdir()
        atomic(candidate / "candidate.json", materialize_loss_decoder(program))
        evaluations = job / "evaluations"
        evaluations.mkdir()
        result = panel.evaluate(candidate, source, evaluations / "matrix", workers=workers, timeout_seconds=None,
                                transport=TrainingStorageTransport(transport, evaluations))
        rows = []
        for cell in result.metrics["matrix"]["cells"]:
            row = {key: cell[key] for key in ("case", "seed", "status", "score", "raw_score", "valid",
                                             "metrics", "error_type", "error_message", "native_failure_diagnostics")
                   if key in cell}
            rows.append(row)
        value = {"formal": False, "assigned": allocated, "program_sha": program_sha,
                 "complete": complete_score(result.metrics, panel), "rows": rows}
        atomic(reply, value)
        return value


def route_seeds(commands, seeds):
    jobs, assigned = {}, set()
    for name, entry in commands.items():
        if isinstance(entry, list):
            entry = {"command": entry, "cells": {name: seeds}}
        panel = {case: [seed for seed in choices if seed in seeds] for case, choices in entry["cells"].items()}
        panel = {case: choices for case, choices in panel.items() if choices}
        if not panel:
            continue
        keys = [(case, seed) for case, chosen in panel.items() for seed in chosen]
        if assigned.intersection(keys) or len(keys) != len(set(keys)):
            raise ValueError("Duplicate case/seed in worker routing")
        assigned.update(keys)
        jobs[name] = (entry["command"], panel)
    if assigned != {(case, seed) for case in CASES for seed in seeds}:
        raise ValueError("Worker routing must cover every requested case and seed")
    return jobs


def worker_output(command, alternate, payload, durable=False):
    """Reconnect accepted work only when the worker persists jobs by request ID."""
    wire = json.dumps(payload)
    if not alternate:
        return subprocess.run(command, input=wire, text=True, encoding="utf-8",
                              stdout=subprocess.PIPE, check=True).stdout
    routes = cycle((command, alternate)) if durable else (command, alternate, command)
    delay = 1
    for attempt, route in enumerate(routes):
        with tempfile.TemporaryFile() as errors:
            result = subprocess.run(route, input=wire, text=True, encoding="utf-8",
                                    stdout=subprocess.PIPE, stderr=errors)
            if result.returncode == 0:
                return result.stdout
            errors.seek(max(0, errors.tell() - 4096))
            tail = errors.read().decode(errors="replace")
        message = tail.lower()
        refused = ("permission denied", "authentication failed", "host key verification failed",
                   "host identification has changed", "bad configuration", "no matching")
        handshake = ("kex_exchange_identification", "banner exchange", "ssh: connect to host")
        network = ("connection reset", "connection closed", "closed by remote host", "connection aborted",
                   "broken pipe", "connection timed out", "operation timed out", "not responding",
                   "network is unreachable", "no route to host", "connection refused")
        pre_auth = any(marker in message for marker in handshake)
        disconnected = any(marker in message for marker in network) or bool(
            re.search(r"connection to [^\n]+ closed\.", message))
        if (result.returncode != 255 or any(marker in message for marker in refused)
                or not (pre_auth or (durable and disconnected))):
            break
        if not durable and attempt == 2:
            break
        print("Worker SSH disconnected; retrying request", payload["request"],
              "on alternate route in", delay, "seconds", flush=True)
        time.sleep(delay)
        delay = min(60, delay * 2)
    raise RuntimeError(f"Worker exited with status {result.returncode}: {tail[-600:]}")


def run_batches(commands, request):
    jobs = route_seeds(commands, request["seeds"])

    def invoke(entry):
        name, (command, panel) = entry
        payload = {key: request[key] for key in ("run", "request", "program")}
        payload["cells"] = panel
        entry = commands[name]
        alternate = entry.get("alternate_command") if isinstance(entry, dict) else None
        durable = isinstance(entry, dict) and entry.get("durable_worker") is True
        reply = json.loads(worker_output(command, alternate, payload, durable))
        if reply.get("assigned") != panel or reply.get("formal") is not False:
            raise ValueError("Mismatched worker receipt")
        return reply

    with ThreadPoolExecutor(max_workers=3) as executor:
        return list(executor.map(invoke, jobs.items()))


def score_replies(replies, seeds, program_sha):
    indexed = {}
    for reply in replies:
        if reply["program_sha"] != program_sha:
            raise ValueError("Worker evaluated a different candidate")
        group = reply["rows"]
        panel = reply["assigned"]
        requested = {(case, seed) for case, choices in panel.items() for seed in choices}
        returned = {(row["case"], row["seed"]) for row in group}
        if len(group) != len(requested) or returned != requested or returned.intersection(indexed):
            raise ValueError("Worker returned an unexpected case/seed pair")
        indexed.update({(row["case"], row["seed"]): row for row in group})
    expected = [(case, seed) for case in CASES for seed in seeds]
    if set(expected) != set(indexed):
        raise ValueError("Missing case/seed in collected results")
    rows = [indexed[key] for key in expected]
    if not all(reply["complete"] for reply in replies) or not all(
            type(row.get("score")) in (int, float) and math.isfinite(row["score"]) for row in rows):
        return rows, None
    return rows, mean(mean(indexed[(case, seed)]["score"] for seed in seeds) for case in CASES)


def store_evaluation(work, request_id, program, replies, seeds):
    digest = hashlib.sha256(program.encode()).hexdigest()
    rows, score = score_replies(replies, seeds, digest)
    evaluation = work / "evaluations" / request_id
    receipt_path = work / "receipts" / (request_id + ".json")
    receipt = {"request_id": request_id, "candidate_id": digest, "source": program,
               "status": "succeeded" if score is not None else "failed",
               "feedback": {"score": score, "cells": rows}, "artifacts_dir": str(evaluation)}
    if receipt_path.exists():
        if json.loads(receipt_path.read_text()) != receipt:
            raise ValueError("Existing receipt differs from the worker results")
        return receipt
    for row in rows:
        folder = evaluation / "cells" / row["case"] / row["seed"] / "result"
        folder.mkdir(parents=True, exist_ok=True)
        atomic(folder / "evaluation_result.json", {"metrics": row.get("metrics", {}), "formal": False})
    atomic(receipt_path, receipt)
    return receipt


def diagnostics(args):
    source, bench, data = framework(args.official)
    from contest2.agent_api import AgentAPIError
    from contest2.agent_workspace import stage_agent
    from contest2.budget import BudgetLedger
    from contest2.model_pricing import MODEL_ID
    from contest2.runner import _gateway_ready, _port, _provider_key
    from local_tasks.tp_gnn_local_task_definitions import DECODER_TASK, validate_program

    full = full_matrix(bench, data)
    commands = json.loads(args.workers.read_text())
    layout = {name: panel for name, (_, panel) in route_seeds(commands, args.seeds).items()}
    work = args.work_root.resolve()
    manifest = {"formal": False, "schedule": "case-pinned-three-gpu", "cases": list(CASES),
                "seeds": args.seeds, "rounds": args.rounds, "allocation": layout}
    if args.resume:
        if json.loads((work / "DIAGNOSTIC_ONLY.json").read_text()) != manifest:
            raise ValueError("Existing development run has a different allocation or budget")
        if not (work / "control/model-budget.sqlite").is_file():
            raise ValueError("Missing development budget ledger")
    else:
        work.mkdir(parents=True)
        atomic(work / "DIAGNOSTIC_ONLY.json", manifest)
    start = validate_program((full.spec.root / "initial_program.py").read_text(), DECODER_TASK)

    class Context:
        task = "loss_decoder"
        baseline_candidate = "published-official-initial"
        evaluation_cells = [{"case": case, "seed": seed} for case in CASES for seed in args.seeds]
        files = {"framework": str(bench), "workspaces": str(work / "workspaces"),
                 "evaluations": str(work / "evaluations")}
        receipts = {}

        def status(self):
            state = ledger.snapshot()
            return {**state, "evaluation_mode": "diagnostic",
                    "evaluations_remaining": args.rounds - len(self.receipts),
                    "evaluation_dispatch_allowed": len(self.receipts) < args.rounds,
                    "history": list(self.receipts.values())}

        def submit_evaluation(self, source_text, request_id):
            program = validate_program(source_text, DECODER_TASK)
            digest = hashlib.sha256(program.encode()).hexdigest()
            if request_id in self.receipts:
                receipt = self.receipts[request_id]
                if receipt["candidate_id"] != digest:
                    raise AgentAPIError("Request ID already belongs to another candidate")
                return receipt
            if len(self.receipts) >= args.rounds:
                raise AgentAPIError("Development evaluation limit reached")
            print("Dispatched three cases for", request_id, digest[:12], flush=True)
            replies = run_batches(commands, {"run": work.name, "request": request_id,
                                              "program": program, "seeds": args.seeds})
            receipt = store_evaluation(work, request_id, program, replies, args.seeds)
            self.receipts[request_id] = receipt
            print("Development score", request_id, receipt["feedback"]["score"], flush=True)
            return receipt

        def wait_evaluation(self, request_id):
            return self.receipts[request_id]

    if not args.resume:
        for name in ("workspaces", "evaluations", "receipts", "control"):
            (work / name).mkdir()
    context = Context()
    if args.baseline_only:
        program = args.reference_program.read_text(encoding="utf-8") if args.reference_program else start
        receipt = context.submit_evaluation(program, "initial")
        if receipt["status"] != "succeeded":
            raise RuntimeError("Three-GPU baseline did not return a complete matrix")
        return
    from diagnose_harness import DiagnosticModel

    agent_path = work / "participant-agent" / context.task
    if args.resume:
        for path in sorted((work / "receipts").glob("*.json"), key=lambda item: item.stat().st_mtime_ns):
            receipt = json.loads(path.read_text())
            program = validate_program(receipt["source"], DECODER_TASK)
            if (receipt["request_id"] != path.stem or
                    receipt["candidate_id"] != hashlib.sha256(program.encode()).hexdigest()):
                raise ValueError(f"Invalid recorded development receipt: {path.name}")
            context.receipts[path.stem] = receipt
        if not context.receipts or not (agent_path / "search.jsonl").is_file():
            raise ValueError("Missing development run history")
    else:
        agent_path = stage_agent(args.agent_dir, agent_path)
    sys.path.insert(0, str(agent_path))
    from agent import Agent

    ledger = BudgetLedger(work / "control/model-budget.sqlite", evaluation_limit=10, model_cost_limit_rmb="15",
                          task_id=context.task, allowed_model=MODEL_ID)
    key = _provider_key(args, source, bench, work)
    port, token = _port(), secrets.token_urlsafe(32)
    gateway_env = {**os.environ, "PYTHONPATH": str(bench), "DEEPSEEK_API_KEY": key, "CONTEST_GATEWAY_TOKEN": token}
    url = f"http://127.0.0.1:{port}/v1"
    with (work / "control/model-gateway.log").open("a") as log, subprocess.Popen(
        [sys.executable, "-B", "-m", "contest2.model_gateway", "--ledger", str(ledger.path),
         "--task", context.task, "--port", str(port)], env=gateway_env, stdout=log, stderr=log
    ) as gateway:
        try:
            _gateway_ready(gateway, url, token)
            context.model = DiagnosticModel(url, token, work / "diagnostic-model.jsonl", AgentAPIError, "high")
            context.model.passthrough = True
            winner = Agent().run(context)
            atomic(work / "diagnostic-result.json", {"formal": False, "selected_candidate_id": winner,
                                                     "rounds": len(context.receipts)})
        finally:
            gateway.terminate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    worker = modes.add_parser("worker")
    worker.add_argument("--official", required=True, type=Path)
    worker.add_argument("--case", choices=CASES, action="append", required=True)
    worker.add_argument("--gpu", type=int, choices=(0, 1), required=True)
    worker.add_argument("--workers", type=int, choices=(1, 2), default=1)
    worker.add_argument("--host-slots", type=int, choices=(1, 2, 3, 4), default=1)
    worker.add_argument("--memory-gib", type=int, choices=(21, 24), default=24)
    coordinator = modes.add_parser("run")
    coordinator.add_argument("--official", required=True, type=Path)
    coordinator.add_argument("--workers", required=True, type=Path)
    coordinator.add_argument("--work-root", required=True, type=Path)
    coordinator.add_argument("--seeds", nargs="+", choices=SEEDS, default=list(SEEDS))
    coordinator.add_argument("--rounds", type=int, default=3, choices=range(1, 11))
    coordinator.add_argument("--resume", action="store_true")
    coordinator.add_argument("--baseline-only", action="store_true")
    coordinator.add_argument("--reference-program", type=Path)
    coordinator.add_argument("--agent-dir", type=Path)
    coordinator.add_argument("--api-key-file", type=Path)
    args = parser.parse_args()
    if args.mode == "worker":
        if args.workers > args.host_slots:
            parser.error("--workers cannot exceed the host-wide slot limit")
        wire = sys.stdin.read(40000)
        if len(wire) == 40000:
            raise ValueError("Worker request exceeds size limit")
        with redirect_stdout(sys.stderr):
            value = physical_case(args.official, args.case, args.gpu, json.loads(wire),
                                  workers=args.workers, host_slots=args.host_slots,
                                  memory_gib=args.memory_gib)
        print(json.dumps(value, ensure_ascii=False))
    else:
        if args.resume and args.baseline_only:
            parser.error("--resume requires an existing candidate search")
        if not args.baseline_only and args.agent_dir is None:
            parser.error("--agent-dir is required for candidate search")
        args.data_root = args.official / "contest-data" / "task2"
        if args.resume:
            with (args.work_root / ".resume.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                diagnostics(args)
        else:
            diagnostics(args)


if __name__ == "__main__":
    main()
