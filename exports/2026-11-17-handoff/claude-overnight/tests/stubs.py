"""Offline stand-ins for the organizer framework and bridge. Development material only."""

import ast
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types

HERE = Path(__file__).resolve().parent
AGENT_DIR = Path(__import__("os").environ.get("AGENT_DIR") or
                 HERE.parent / "next-harness" / "AgenticBench" / "agent" / "loss_decoder")
DECODER_TASK = "tp_gnn_loss_decoder"
FUNCTIONS = ["compute_tp_gnn_loss", "decode_tp_gnn_embeddings"]

# official/reference/published_training_reference.json
PUBLISHED = {
    "ariane133-ng45": (0.5290353246723486, 96.42498143235612, {
        "1001": (-0.46473759489492794, -22.69812846368777),
        "1002": (-0.511323442504157, -101.00025635050363),
        "1003": (-0.5738236714876622, -29.767709140211068)}),
    "bp-ng45": (8.663351750761597, 6622.78575944895, {
        "1001": (-8.392474508445966, -9059.339646875793),
        "1002": (-7.841612026113778, -10349.946316496395),
        "1003": (-7.870566643414895, -8622.276498609612)}),
    "bp_fe-ng45": (0.9002498352590634, 716.9190029865956, {
        "1001": (-0.6611195111821111, -174.72074415142822),
        "1002": (-0.7280568576313236, -211.7487329856929),
        "1003": (-0.639466275808939, -188.35428327940795)}),
}
CELLS = [{"case": case, "seed": seed} for case in ("bp_fe-ng45", "bp-ng45", "ariane133-ng45")
         for seed in ("1001", "1002", "1003")]

INITIAL = '''# EVOLVE-BLOCK-START
def compute_tp_gnn_loss(
    positive_scores,
    negative_scores,
    embeddings,
    positive_sources,
    positive_targets,
    negative_sources,
    negative_targets,
    source_batch_size,
    epoch,
    max_epochs,
    graph_scores,
    graph_sources,
    graph_targets,
    graph_net_ids,
    graph_weights,
    net_weights,
    node_features,
    node_areas,
):
    """Reproduce the maintained random-walk negative-sampling objective."""
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
# EVOLVE-BLOCK-END
'''


def variant(loss_body=None, decoder_body=None):
    """The initial program with one function body replaced (fixture programs for scripted replies)."""
    tree_lines = INITIAL.splitlines()
    text = "\n".join(tree_lines)
    if loss_body:
        text = text.replace('    """Reproduce the maintained random-walk negative-sampling objective."""\n    return -(\n'
                            '        F.logsigmoid(positive_scores).sum()\n        + F.logsigmoid(-negative_scores).sum()\n'
                            '    ) / max(1, source_batch_size)', loss_body)
    if decoder_body:
        text = text.replace('    """Reproduce the frozen area-balanced global two-way decoder."""\n'
                            '    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)',
                            decoder_body)
    return text + "\n"


def score_metrics(case, raw):
    wns_ref, tns_ref, _ = PUBLISHED[case]
    wns = (wns_ref - max(0.0, -raw["final_global_wns_setup_ns"])) / wns_ref
    tns = (tns_ref - max(0.0, -raw["final_global_tns_setup_ns"])) / tns_ref
    return {**raw, "wns_deficit_improvement": wns, "tns_deficit_improvement": tns,
            "combined_score": max(-100.0, 100 * (0.4 * wns + 0.6 * tns))}


def validate_program(source, task):
    tree = ast.parse(source)
    if [getattr(node, "name", None) for node in tree.body] != FUNCTIONS:
        raise ValueError("Return exactly the two editable functions in their original order")
    return source.strip() + "\n"


class AgentAPIError(RuntimeError):
    pass


def install():
    def module(name, **attributes):
        created = types.ModuleType(name)
        created.__dict__.update(attributes)
        sys.modules[name] = created

    module("contest2", __path__=[])
    module("contest2.agent_api", AgentAPIError=AgentAPIError)
    module("contest2.model_pricing", MODEL_ID="deepseek-v4.1-flash")
    module("contest2.scoring", score_metrics=score_metrics, reference_table=lambda: {"cases": {
        case: {"split": "train", "measurements": {"loss_decoder": {
            seed: {"wns_ns": wns, "tns_ns": tns} for seed, (wns, tns) in seeds.items()}}}
        for case, (_, _, seeds) in PUBLISHED.items()}})
    module("local_tasks", __path__=[])
    module("local_tasks.tp_gnn_local_task_definitions", DECODER_TASK=DECODER_TASK, validate_program=validate_program,
           DECODER_ARGS=("embeddings", "node_areas", "seed", "max_iterations", "balance_target"),
           DECODER_HELPERS={"np", "reference_global_two_way"}, LOSS_HELPERS={"torch", "F"},
           LEGACY_LOSS_ARGS=tuple(ast.parse(INITIAL).body[0].args.args[index].arg for index in range(18)))
    module("local_bench", __path__=[])
    module("local_bench.program_safety", normalized_program=lambda source: source)


def load_agent(workdir, opening=None, log_events=()):
    """Import a private copy of the Agent directory, optionally with opening.txt and a prior search log."""
    install()
    copy = Path(workdir) / "agent"
    shutil.copytree(AGENT_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "search.jsonl", "opening.txt"))
    if opening:
        (copy / "opening.txt").write_text(opening + "\n", encoding="utf-8")
    if log_events:
        (copy / "search.jsonl").write_text("".join(json.dumps(event) + "\n" for event in log_events), encoding="utf-8")
    for name in ("agent", "paired_feedback", "candidate_reply"):
        sys.modules.pop(name, None)
    sys.path.insert(0, str(copy))
    try:
        agent = importlib.import_module("agent")
    finally:
        sys.path.remove(str(copy))
    agent.time.sleep = lambda seconds: None
    return agent, copy


def completed(text):
    return {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 1, "output_tokens": 1}}


INCOMPLETE = {"status": "incomplete", "output": [], "usage": {"input_tokens": 1, "output_tokens": 16384}}


class Bridge:
    """AgentContext look-alike. `receipts` are replayed in order; `evaluate(source, request_id)` makes new ones."""

    task = "loss_decoder"
    baseline_candidate = "official-initial"

    def __init__(self, workdir, model, evaluate=None, receipts=(), evaluation_limit=10, model_limit=200):
        root = Path(workdir)
        task = root / "framework" / "local_tasks" / DECODER_TASK
        task.mkdir(parents=True)
        (task / "initial_program.py").write_text(INITIAL, encoding="utf-8")
        (task / "prompt.md").write_text("# Official numerical interface (offline placeholder)\n", encoding="utf-8")
        for name in ("workspaces", "evaluations"):
            (root / name).mkdir()
        self.root = root
        self.files = {"framework": str(root / "framework"), "workspaces": str(root / "workspaces"),
                      "evaluations": str(root / "evaluations")}
        self.evaluation_cells = [dict(cell) for cell in CELLS]
        self.model_reply, self.evaluate = model, evaluate
        self.evaluation_limit, self.model_limit = evaluation_limit, model_limit
        self.records, self.order, self.requests = {}, [], []
        self.faults = {"status": 0, "wait": 0, "submit": 0}
        self.model = types.SimpleNamespace(responses_create=self._model)
        for receipt in receipts:
            self.store(receipt)

    def store(self, receipt):
        """Keep a receipt and write the organizer's native partition diagnostics next to it."""
        receipt = dict(receipt)
        partition = receipt.pop("partition", {})
        artifacts = self.root / "evaluations" / receipt["request_id"]
        for key, change in partition.items():
            case, seed = key.split("/")
            native = artifacts / "cells" / case / seed / "result"
            native.mkdir(parents=True, exist_ok=True)
            (native / "evaluation_result.json").write_text(json.dumps({"metrics": change}), encoding="utf-8")
        receipt["artifacts_dir"] = str(artifacts)
        self.records[receipt["request_id"]] = receipt
        self.order.append(receipt["request_id"])
        return receipt

    def _model(self, payload):
        if len(self.requests) >= self.model_limit:
            raise AgentAPIError("model budget exhausted")
        system, user = (message["content"] for message in payload["input"])
        request = json.loads(user)
        self.requests.append({"effort": payload["reasoning"]["effort"], "system": system, "request": request})
        return self.model_reply(self, system, request)

    def _fault(self, name):
        if self.faults[name]:
            self.faults[name] -= 1
            raise AgentAPIError("Agent bridge communication failed; request outcome is unknown")

    def status(self):
        self._fault("status")
        remaining = self.evaluation_limit - len(self.order)
        return {"history": [{"request_id": request_id} for request_id in self.order],
                "evaluations_remaining": remaining, "evaluation_dispatch_allowed": remaining > 0,
                "model_dispatch_allowed": len(self.requests) < self.model_limit, "model_stop_reasons": []}

    def wait_evaluation(self, request_id, poll_seconds=5):
        self._fault("wait")
        return self.records[request_id]

    def submit_evaluation(self, source, request_id=None):
        self._fault("submit")
        if request_id in self.records:
            return self.records[request_id]
        if len(self.order) >= self.evaluation_limit:
            raise AgentAPIError("evaluation budget exhausted")
        return self.store({"request_id": request_id, "source": source, **self.evaluate(self, source, request_id)})

    def plans(self):
        return [row for row in self.requests if row["effort"] == "high"
                or row["system"].startswith("Return a short experiment plan")]

    def generations(self):
        return [row for row in self.requests if row not in self.plans()]


def cells_with(points, base=None, status="succeeded"):
    """Official-looking cells: published timing shifted by `points` of TNS score per cell."""
    cells = []
    for cell in CELLS:
        wns_ref, tns_ref, seeds = PUBLISHED[cell["case"]]
        wns, tns = seeds[cell["seed"]]
        shift = (points.get((cell["case"], cell["seed"]), 0.0) if isinstance(points, dict) else points)
        metrics = score_metrics(cell["case"], {"final_global_wns_setup_ns": wns,
                                               "final_global_tns_setup_ns": tns + shift / 60 * tns_ref,
                                               "cut_net_count": 3000, "timing_weighted_cut": 5000.0})
        cells.append({**cell, "status": status, "valid": True, "score": metrics["combined_score"],
                      "raw_score": metrics["combined_score"], "metrics": metrics})
    return cells


def official_score(cells):
    cases = sorted({cell["case"] for cell in cells})
    return sum(sum(cell["score"] for cell in cells if cell["case"] == case) /
               sum(1 for cell in cells if cell["case"] == case) for case in cases) / len(cases)


def broad_partition(fraction=0.02):
    return {f"{cell['case']}/{cell['seed']}": {
        "partition_assignment_identical": 0, "partition_assignment_changed_count": int(fraction * 50000),
        "partition_assignment_changed_fraction": fraction, "tp_gnn_repair_moved_area_fraction": 0.0} for cell in CELLS}


def workdir():
    return tempfile.mkdtemp(prefix="next-harness-test-")
