"""Run a paired, synthetic numerical experiment using the released candidate runtime."""

import ast
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile


INTERFACE = "tp-gnn-loss-decoder-v1"
CLAIM = re.compile(r"\bProbe:\s*halve_feature\[([0-9])\]\s*->\s*"
                   r"(endpoint_grad_norm|incident_score_grad_norm)\s+(up|down)\b", re.I)


def run_experiment(source_root, parent, candidate, components):
    if not source_root:
        return {"status": "unavailable", "reason": "Native source mount not supplied"}
    payload = dict(source_root=str(source_root), parent=parent, candidate=candidate,
                   components=list(components))
    try:
        result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve())],
                                input=json.dumps(payload), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, encoding="utf-8", timeout=60)
        if result.returncode:
            return {"status": "unavailable", "reason": (result.stderr[-250:] or str(result.returncode))}
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {"status": "unavailable", "reason": str(error)[:250]}


def loss_observation(function, points, column=None):
    import torch

    embedding = points.clone().requires_grad_(True)
    # Four unequal nets rooted at their smallest endpoint. Sampled pairs are separate.
    src = torch.tensor([0, 0, 0, 1, 3, 3, 5])
    dst = torch.tensor([1, 2, 4, 5, 4, 6, 7])
    ids = torch.tensor([0, 0, 0, 1, 2, 2, 3])
    nets = torch.tensor([1.4, 1., 1.8, 1.2])
    weights = nets[ids] / torch.tensor([3., 3., 3., 1., 2., 2., 1.])
    positive = torch.tensor([0, 1, 2, 3, 4])
    negative = torch.tensor([3, 7, 5, 0, 1])
    targets = torch.tensor([2, 5, 4, 6, 7])
    def dot(left, right):
        return (embedding[left] * embedding[right]).sum(dim=1)
    edges = dot(src, dst)
    i = torch.arange(8, dtype=points.dtype)
    features = torch.stack((-0.1 - i / 50, -0.05 - i / 80, 0.3 + i / 8,
                            0.4 + i / 9, 1.5 + i / 12, 0.2 + i / 10, 1 - i / 16,
                            4 + i, 2 + i.remainder(3), 4 + i.remainder(4)), dim=1)
    if column is not None:
        features[0, column] *= 0.5
    loss = function(dot(positive, targets), dot(positive, negative), embedding, positive,
                    targets, positive, negative, len(positive), 2, 20, edges, src, dst,
                    ids, weights, nets, features, 1 + i)
    if not isinstance(loss, torch.Tensor) or loss.ndim or not torch.isfinite(loss).item():
        raise ValueError("expected one finite scalar loss")
    gradient, score_gradient = torch.autograd.grad(loss, (embedding, edges), allow_unused=True)
    if gradient is None or not torch.isfinite(gradient).all().item():
        raise ValueError("missing or nonfinite embedding gradient")
    if score_gradient is not None and not torch.isfinite(score_gradient).all().item():
        raise ValueError("nonfinite graph-score gradient")
    incident = (src == 0) | (dst == 0)
    if score_gradient is None:
        score_gradient = torch.zeros_like(edges)
    observation = {"loss": loss.item(), "endpoint_grad_norm": gradient[0].double().norm().item(),
                   "incident_score_grad_norm": score_gradient[incident].double().norm().item()}
    return observation, gradient, score_gradient


def measure(payload):
    import torch
    from src.partition.lol.methods.tp_gnn import area_balanced_weighted_kmeans
    from src.partition.lol.methods.tp_gnn_evolution import decode_evolution_embeddings, load_evolution_program

    torch.set_num_threads(1)
    points = torch.nn.functional.normalize(torch.randn(8, 16, generator=torch.Generator().manual_seed(43)), dim=1)
    doc = ast.get_docstring(ast.parse(payload["candidate"]).body[0]) or ""
    claim = CLAIM.search(doc) if "loss" in payload["components"] else None
    report = {"status": "observed", "fixture": "synthetic-8-v1", "components": payload["components"]}
    parent_gradients = {}
    if claim:
        column, metric, direction = claim.groups()
        metric, direction = metric.lower(), direction.lower()
        report["claim"] = {"node": 0, "halved_feature": int(column), "metric": metric, "direction": direction}
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "capsule.json"
        for role in ("parent", "candidate"):
            path.write_text(json.dumps({"interface_version": INTERFACE, "source": payload[role]}), encoding="utf-8")
            observation = report[role] = {}
            try:
                functions, provenance = load_evolution_program(path, INTERFACE, area_balanced_weighted_kmeans)
                if "loss" in payload["components"]:
                    loss = functions["compute_tp_gnn_loss"]
                    conditions = [("base", None)]
                    if claim:
                        conditions.append(("perturbed", int(column)))
                    for condition, feature in conditions:
                        values, embedding_grad, edge_grad = loss_observation(loss, points, feature)
                        observation[condition] = values
                        if role == "parent":
                            parent_gradients[condition] = (embedding_grad, edge_grad)
                        else:
                            parent_embedding, parent_edges = parent_gradients[condition]
                            report.setdefault("paired_difference", {})[condition] = {
                                "max_abs_embedding_grad_delta": (embedding_grad - parent_embedding).abs().max().item(),
                                "max_abs_edge_grad_delta": (edge_grad - parent_edges).abs().max().item(),
                            }
                if "decoder" in payload["components"]:
                    labels, _ = decode_evolution_embeddings(functions, points.numpy(), list(range(1, 9)),
                                                           43, 50, 0.5, provenance)
                    observation["labels"] = labels
                    if role == "candidate":
                        report.setdefault("paired_difference", {})["changed_labels"] = sum(
                            a != b for a, b in zip(report["parent"]["labels"], labels))
            except (TypeError, RuntimeError, ArithmeticError, IndexError, ValueError) as error:
                report.update(status="candidate_error" if role == "candidate" else "unavailable",
                              reason=f"{role}: {type(error).__name__}: {str(error)[:220]}")
                return report
    if claim:
        base = report["candidate"]["base"][metric]
        perturbed = report["candidate"]["perturbed"][metric]
        if math.isclose(base, perturbed, rel_tol=1e-5, abs_tol=1e-8):
            observed = "unchanged"
        else:
            observed = "up" if perturbed > base else "down"
        report["observed_direction"] = observed
        report["status"] = "supported_on_fixture" if direction == observed else "claim_mismatch"
    return report


if __name__ == "__main__":
    data = json.load(sys.stdin)
    sys.path.insert(0, str(Path(data["source_root"]) / "Place-3D"))
    try:
        print(json.dumps(measure(data), allow_nan=False))
    except (ImportError, OSError, ValueError) as error:
        print(json.dumps({"status": "unavailable", "reason": str(error)[:250]}))
