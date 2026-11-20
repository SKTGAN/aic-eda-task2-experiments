"""Run three development-only Harness rounds on a selected training subset."""

import argparse
from contextlib import contextmanager
from decimal import Decimal
from hashlib import sha256
from importlib import import_module
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import urllib.request
from uuid import uuid4


HERE = Path(__file__).resolve().parent
BASELINE = "loss_decoder"
ROUNDS = 3
HYPOTHESIS_PROMPT = (
    "For this planning call, replace the earlier response format with a plain-text plan. "
    "Plan one candidate edit for this development run. In at most 150 words, give the "
    "parent's relevant decision, the one mechanism to change, the evidence supporting it, "
    "and what would falsify it. Keep the requested edit scope and use only the supplied "
    "interface. Treat case and seed data as observations. Return a plan without code."
)


def select_panel(table, seeds_per_case, fixed_seed=None):
    panel = {}
    for case in ("bp_fe-ng45", "bp-ng45", "ariane133-ng45"):
        entry = table["cases"][case]
        measurements = entry["measurements"][BASELINE]
        def score(sample):
            wns = max(0, -sample["wns_ns"]) / entry["reference_wns_deficit_ns"]
            tns = max(0, -sample["tns_ns"]) / entry["reference_tns_deficit_ns"]
            return max(-100, 100 * (1 - 0.4 * wns - 0.6 * tns))
        ranked = sorted((score(sample), seed) for seed, sample in measurements.items())
        chosen = [(value, seed) for value, seed in ranked if seed == fixed_seed] if fixed_seed else ranked[:seeds_per_case]
        if not chosen:
            raise ValueError(f"No published seed {fixed_seed!r} for {case}")
        panel[case] = [{"seed": seed, "reference_score": value} for value, seed in chosen]
    return panel


def make_matrix(full, panel):
    by_case = {case: [row["seed"] for row in rows] for case, rows in panel.items()}
    picks = {(case, seed) for case, seeds in by_case.items() for seed in seeds}
    rows = [{key: cell[key] for key in ("case", "seed", "base_config", "baseline_run", "reference_run")}
            for cell in full.cells if (cell["case"], cell["seed"]) in picks]
    if len(rows) != len(picks) or len(rows) >= len(full.cells):
        raise ValueError("Expected a strict subset of the admitted training matrix")
    return {"schema_version": 2, "task": full.spec.task_id, "cases": list(panel),
            "case_seeds": by_case, "seeds": [row for row in full.seeds
                                            if any(row["id"] in seeds for seeds in by_case.values())],
            "cells": rows}


class DiagnosticModel:
    def __init__(self, url, token, log_path, api_error, effort):
        self.url, self.token = url, token
        self.log_path, self.api_error = log_path, api_error
        self.effort = effort
        self.plans = {}
        self.passthrough = False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def log(self, event):
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    def send(self, payload, purpose):
        call_id = uuid4().hex
        self.log({"event": "model_request", "call_id": call_id, "purpose": purpose, "payload": payload})
        request = urllib.request.Request(self.url + "/responses", data=json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"}, method="POST")
        try:
            with self.opener.open(request, timeout=1800) as response:
                result = json.load(response)
        except (OSError, ValueError) as error:
            status = getattr(error, "code", None)
            self.log({"event": "model_response", "call_id": call_id, "status": "gateway_error", "http_status": status})
            if status in (400, 422):
                raise self.api_error(f"Gateway rejected the {purpose} request (HTTP {status})") from error
            # An uncertain provider call stays in the metered ledger. Do not repeat it here.
            raise RuntimeError(f"Gateway {purpose} request failed. Check the diagnostic model ledger.") from error
        if not isinstance(result, dict):
            raise self.api_error(f"Invalid {purpose} reply from the model gateway")
        visible = "\n".join(part["text"] for item in result.get("output") or []
                            if isinstance(item, dict) and item.get("type") == "message"
                            for part in item.get("content") or []
                            if isinstance(part, dict) and part.get("type") == "output_text"
                            and isinstance(part.get("text"), str))
        self.log({"event": "model_response", "call_id": call_id, "status": result.get("status"),
                  "output_text": visible, "usage": result.get("usage")})
        return result, visible

    def responses_create(self, payload):
        if self.passthrough:
            purpose = "plan" if payload.get("reasoning", {}).get("effort") == "high" else "candidate_generation"
            return self.send(payload, purpose)[0]
        user = json.loads(payload["input"][1]["content"])
        if "decision" not in user:
            purpose = "opening_review" if "proposals" in user else "opening_alternative"
            if purpose == "opening_review":
                payload = {**payload, "reasoning": {"effort": self.effort}}
            return self.send(payload, purpose)[0]
        key = (user["evaluations_remaining"], user["search_intent"], user["parent_id"])
        if key not in self.plans:
            messages = [dict(message) for message in payload["input"]]
            messages[0]["content"] += "\n\n" + HYPOTHESIS_PROMPT
            plan, text = self.send({**payload, "reasoning": {"effort": self.effort}, "input": messages}, "plan")
            self.plans[key] = text[:2400] if plan.get("status") == "completed" else ""
        if self.plans[key]:
            user["diagnostic_plan"] = self.plans[key]
            messages = [dict(message) for message in payload["input"]]
            messages[1]["content"] = json.dumps(user, ensure_ascii=False)
            payload = {**payload, "input": messages}
        return self.send(payload, "candidate_generation")[0]


class DiagnosticContext:
    task = BASELINE
    baseline_candidate = "published-official-initial"
    evaluation_mode = "diagnostic"

    def __init__(self, matrix, source, root, transport, ledger, model):
        self.matrix, self.source, self.root = matrix, source, root
        self.transport, self.ledger, self.model = transport, ledger, model
        self.receipts = {}
        self.evaluation_cells = [{"case": row["case"], "seed": row["seed"]} for row in matrix.cells]
        self.files = {"framework": str(source / "AgenticBench"), "workspaces": str(root / "workspaces"),
                      "evaluations": str(root / "evaluations")}
        for name in ("workspaces", "evaluations", "candidates", "receipts"):
            (root / name).mkdir()

    def status(self):
        state = self.ledger.snapshot()
        return {**state, "evaluation_mode": "diagnostic", "evaluations_remaining": ROUNDS - len(self.receipts),
                "evaluation_dispatch_allowed": len(self.receipts) < ROUNDS,
                "history": list(self.receipts.values())}

    def submit_evaluation(self, source, request_id):
        from contest2.agent_api import AgentAPIError
        from contest2.scoring import complete_score
        from contest2.storage import TrainingStorageTransport
        from grt_bench.common import write
        from local_tasks.tp_gnn_local_task_definitions import materialize_loss_decoder, validate_program

        program = validate_program(source, self.matrix.spec.task_id)
        candidate = sha256((self.matrix.identity + program).encode()).hexdigest()
        if request_id in self.receipts:
            receipt = self.receipts[request_id]
            if receipt["candidate_id"] != candidate:
                raise AgentAPIError("Request ID already belongs to another candidate")
            return receipt
        if len(self.receipts) >= ROUNDS:
            raise AgentAPIError("Diagnostic candidate limit reached")
        if not request_id or not all(char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                                     for char in request_id):
            raise AgentAPIError("Invalid diagnostic request ID")
        candidate_dir = self.root / "candidates" / candidate
        if not candidate_dir.exists():
            write(candidate_dir / "candidate.json", materialize_loss_decoder(program))
        evaluations = self.root / "evaluations"
        print(f"Diagnostic candidate {len(self.receipts) + 1}/{ROUNDS}: {candidate[:12]}", flush=True)
        result = self.matrix.evaluate(candidate_dir, self.source, evaluations / request_id,
            transport=TrainingStorageTransport(self.transport, evaluations, retain_physical_files=False),
            workers=1, timeout_seconds=None)
        metrics = result.metrics
        valid = complete_score(metrics, self.matrix)
        matrix = metrics["matrix"]
        rows = [{key: cell[key] for key in ("case", "seed", "status", "score", "valid", "metrics", "error_type",
                                         "error_message", "native_failure_diagnostics") if key in cell}
                for cell in matrix["cells"]]
        receipt = {"request_id": request_id, "candidate_id": candidate, "source": program,
                   "status": "succeeded" if valid else "failed", "reason": None if valid else "Incomplete diagnostic panel",
                   "feedback": {"score": metrics.get("combined_score"), "cells": rows,
                                "cases": matrix["cases"], "valid": metrics.get("valid", False)}}
        write(self.root / "receipts" / f"{request_id}.json", receipt)
        self.receipts[request_id] = receipt
        print("Diagnostic score:", receipt["feedback"]["score"], flush=True)
        return receipt

    def wait_evaluation(self, request_id):
        return self.receipts[request_id]


def run(args, panel):
    source = args.official / "contest-source"
    framework = source / "AgenticBench"
    args.data_root = args.official / "contest-data" / "task2"
    sys.path.insert(0, str(framework))
    from contest2.agent_api import AgentAPIError
    from contest2.agent_workspace import stage_agent
    from contest2.budget import BudgetLedger
    from contest2.model_pricing import MODEL_ID
    from contest2.runner import _gateway_ready, _port, _provider_key, _runtime, TASK_IDS
    from contest2.runtime_images import gpu_preflight
    from contest2.sampling import validate_public_matrix
    from contest2.scoring import validate_scoring_references
    from grt_bench.common import write
    from local_bench.matrix import LocalEvaluationMatrix
    from local_bench.model import load_task

    root = args.work_root.resolve()
    if any(root == path or path in root.parents for path in (source, args.data_root, args.agent_dir)):
        raise ValueError("Use a separate diagnostic work directory")
    root.mkdir(parents=True, exist_ok=False)
    write(root / "DIAGNOSTIC_ONLY.json", {"formal": False, "candidate_limit": ROUNDS, "panel": panel})
    spec = load_task(framework / "local_tasks" / TASK_IDS[BASELINE])
    full = LocalEvaluationMatrix(args.data_root / BASELINE / "train/qualified_matrix.json", spec)
    validate_public_matrix(full, BASELINE, "train")
    validate_scoring_references(full, BASELINE)
    write(root / "panel.json", make_matrix(full, panel))
    matrix = LocalEvaluationMatrix(root / "panel.json", spec)
    transport, runtime = _runtime(args.runtime, work_root=root, private_queue=True)
    gpu_preflight(runtime["image"], root, runtime["capacity"]["gpus"])
    if args.dev_memory_gib is not None:
        from local_bench.matrix_docker import DockerMatrixTransport

        class DevelopmentTransport(DockerMatrixTransport):
            # Keep the normal scheduler and host admission check, but request a smaller
            # container for this diagnostic. Nothing here is loaded by contest2 run.
            @contextmanager
            def lease(self, folder, resources):
                with super().lease(folder, {**resources, "memory_gb": args.dev_memory_gib}) as claim:
                    yield claim

            def run_phased(self, request, run_path, image, resources, claim, mounts):
                return super().run_phased(request, run_path, image,
                    {**resources, "memory_gb": args.dev_memory_gib}, claim, mounts)

        if args.dev_memory_gib > runtime["capacity"]["memory_gb"]:
            raise ValueError("Development memory exceeds the registered runtime capacity")
        transport = DevelopmentTransport(queue=runtime["queue"], host=runtime["host"], image=runtime["image"])
    agent_dir = stage_agent(args.agent_dir, root / "participant-agent" / BASELINE)
    sys.path.insert(0, str(agent_dir))
    agent = import_module("agent").Agent()

    # The gateway meters only model calls. Sampled evaluations stay in the diagnostic receipts.
    ledger = BudgetLedger(root / "control/model-budget.sqlite", evaluation_limit=10,
                          model_cost_limit_rmb=Decimal("15"), task_id=BASELINE, allowed_model=MODEL_ID)
    key = _provider_key(args, source, framework, root)
    port, token = _port(), secrets.token_urlsafe(32)
    url = f"http://127.0.0.1:{port}/v1"
    env = {**os.environ, "PYTHONPATH": str(framework), "DEEPSEEK_API_KEY": key, "CONTEST_GATEWAY_TOKEN": token}
    with (root / "control/model-gateway.log").open("a") as output, subprocess.Popen(
        [sys.executable, "-B", "-m", "contest2.model_gateway", "--ledger", str(ledger.path),
         "--task", BASELINE, "--port", str(port)], env=env, stdout=output, stderr=output
    ) as gateway:
        try:
            _gateway_ready(gateway, url, token)
            model = DiagnosticModel(url, token, root / "diagnostic-model.jsonl", AgentAPIError, args.planning_effort)
            model.passthrough = getattr(agent, "uses_separate_planning", False)
            context = DiagnosticContext(matrix, source, root, transport, ledger, model)
            selected = agent.run(context)
            write(root / "diagnostic-result.json", {"formal": False, "selected_candidate_id": selected,
                "model_cost_rmb": ledger.snapshot()["model_cost_spent_rmb"], "rounds": len(context.receipts)})
        finally:
            gateway.terminate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, default=HERE / "official")
    parser.add_argument("--agent-dir", type=Path, default=HERE.parent / "next-harness/AgenticBench/agent/loss_decoder")
    parser.add_argument("--seeds-per-case", type=int, choices=(1, 2), default=1)
    parser.add_argument("--seed", choices=("1001", "1002", "1003"), help="Use the same fixed seed in all three cases")
    parser.add_argument("--dev-memory-gib", type=int, choices=range(6, 11), help="Development container cap only")
    parser.add_argument("--planning-effort", choices=("low", "high"), default="high")
    parser.add_argument("--plan", action="store_true", help="Print the selected panel without using Docker or the API")
    parser.add_argument("--work-root", type=Path, help="New directory for the diagnostic run")
    parser.add_argument("--runtime", type=Path, help="Official runtime configuration for an idle GPU host")
    parser.add_argument("--api-key-file", type=Path, help="Existing provider key file outside the work tree")
    args = parser.parse_args()
    args.official = args.official.resolve(strict=True)
    reference = args.official / "contest-source/AgenticBench/contest2/manifests/common-timing-reference.json"
    panel = select_panel(json.loads(reference.read_text(encoding="utf-8")), args.seeds_per_case, args.seed)
    if args.dev_memory_gib and args.seed is None:
        parser.error("--dev-memory-gib requires a fixed --seed")
    print(json.dumps({"formal": False, "rounds": ROUNDS, "memory_gib": args.dev_memory_gib,
                      "panel": panel}, indent=2), flush=True)
    if not args.plan:
        if args.work_root is None or args.runtime is None:
            parser.error("a live run requires --work-root and --runtime")
        args.agent_dir = args.agent_dir.resolve(strict=True)
        run(args, panel)


if __name__ == "__main__":
    main()
