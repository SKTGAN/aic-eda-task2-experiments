"""Single-process CPU experiment on generated inputs, using the contest's candidate loader."""
import ast
import json
from pathlib import Path
import sys
import tempfile


class InvalidOutput(ValueError):
    """An observed output violates a numerical interface condition."""


def parts(source):
    return [ast.get_source_segment(source, node) for node in ast.parse(source).body]


def fixture(torch, seed):
    # Equal initial embeddings and batches for every arm. A second graph has skewed group areas.
    g = torch.Generator().manual_seed(seed)
    n = 40 if seed == 17 else 56
    nodes = torch.arange(n)
    areas = torch.ones(n) if seed == 17 else 1 + (nodes % 9).float().square()
    x = torch.randn(n, 128, generator=g) * 0.12
    x[:, 0] += (nodes % 3).float() / 6
    features = torch.rand(n, 10, generator=g)
    features[:, :2] *= -1
    features[:, 6] = (nodes % 4 != 0).float()
    features[::4, :6] = 0
    features[:, 7:] = (features[:, 7:] * 12).round()
    anchors = nodes[::2][:-2]
    src, dst = anchors.repeat_interleave(2), torch.stack((anchors + 1, anchors + 3), dim=1).flatten()
    net_ids = torch.arange(len(anchors)).repeat_interleave(2)
    net_weights = 1 + torch.rand(len(anchors), generator=g)
    samples = nodes[::2]
    return (x, areas, features, src, dst, net_ids, net_weights, samples, (samples+1) % n, (samples+7) % n)


def simulate(functions, seed, steps, torch, np):
    import torch.nn.functional as F
    x, areas, feat, src, dst, net_ids, net_w, sample, pos, neg = fixture(torch, seed)
    first_loss, first_gradient = None, None
    for epoch in range(steps):
        x = x.detach().requires_grad_(True)
        z = F.normalize(x, dim=1)
        loss = functions["compute_tp_gnn_loss"](
            (z[sample]*z[pos]).sum(1), (z[sample]*z[neg]).sum(1), z, sample, pos, sample, neg,
            len(sample), epoch, 8, (z[src]*z[dst]).sum(1), src, dst, net_ids, net_w[net_ids]/2,
            net_w, feat, areas)
        if not isinstance(loss, torch.Tensor) or loss.ndim != 0 or not torch.isfinite(loss).item() or not loss.requires_grad:
            raise InvalidOutput("loss must return one finite differentiable scalar")
        grad, = torch.autograd.grad(loss, x, allow_unused=True)
        if grad is None or not torch.isfinite(grad).all().item():
            raise InvalidOutput("loss gradient to embeddings is absent or nonfinite")
        if epoch == 0:
            first_loss, first_gradient = loss.item(), grad.detach().flatten()
        x = x - 0.25*grad
    embedding = F.normalize(x.detach(), dim=1).numpy().copy()
    weights = areas.numpy().copy()
    embedding.setflags(write=False)
    weights.setflags(write=False)
    labels = np.asarray(functions["decode_tp_gnn_embeddings"](embedding, weights, seed, 50, 0.5))
    if (labels.shape != weights.shape or not np.issubdtype(labels.dtype, np.integer)
            or not np.array_equal(np.unique(labels), [0, 1])):
        raise InvalidOutput("decoder must return one integer 0/1 label per group, with both sides nonempty")
    cut = np.any((labels[src.numpy()] != labels[dst.numpy()]).reshape(-1, 2), axis=1)
    # Rank ambiguous groups by distance to the two area-weighted centroids of the raw partition.
    # This describes the geometry even when a custom decoder uses a different decision rule.
    distances = []
    for side in (0, 1):
        chosen = labels == side
        center = np.average(embedding[chosen], axis=0, weights=weights[chosen])
        distances.append(np.square(embedding - center).sum(axis=1))
    boundary = np.argsort(np.abs(distances[0] - distances[1]), kind="stable")[:max(1, len(labels)//4)]
    return first_gradient, labels, boundary, {"loss": round(first_loss, 7),
                                  "grad_norm": round(first_gradient.norm().item(), 7),
                                  "raw_top_area_share": round(float(weights[labels == 1].sum()/weights.sum()), 6),
                                  "raw_weighted_cut": round(float(net_w.numpy()[cut].sum()), 6)}


def relative(control, arm, torch):
    base_grad, base_labels, boundary, _ = control
    grad, labels, _, stats = arm
    denom = base_grad.norm().item() * grad.norm().item()
    count = int((labels != base_labels).sum())
    aligned = 1-labels if count > len(labels)/2 else labels
    return {**stats, "first_gradient_cosine": round(torch.dot(base_grad, grad).item()/denom, 6) if denom else None,
            "control_boundary_quartile": len(boundary),
            "boundary_changed_up_to_flip": (int((aligned[boundary] != base_labels[boundary]).sum())
                                            if 2*count != len(labels) else None),
            "raw_changed": count, "raw_changed_up_to_flip": min(count, len(labels)-count), "groups": len(labels)}


def experiment(payload, mode):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    sys.path.insert(0, payload["place"])
    from src.partition.lol.methods.tp_gnn import area_balanced_weighted_kmeans
    from src.partition.lol.methods.tp_gnn_evolution import load_evolution_program
    control, candidate = parts(payload["control"]), parts(payload["candidate"])
    arms = {"control": control, "candidate": candidate}
    if mode == "ablation":
        arms.update(loss_only=[candidate[0], control[1]], decoder_only=[control[0], candidate[1]])
    results = []
    with tempfile.TemporaryDirectory() as temp:
        capsule = Path(temp) / "candidate.json"
        functions = {}
        pairs = {name: tuple(pair) for name, pair in arms.items()}
        for pair in dict.fromkeys(pairs.values()):
            capsule.write_text(json.dumps({"interface_version": "tp-gnn-loss-decoder-v1", "source": "\n\n".join(pair)}),
                               encoding="utf-8")
            functions[pair], _ = load_evolution_program(capsule, "tp-gnn-loss-decoder-v1", area_balanced_weighted_kmeans)
        for seed in ((17,) if mode == "contract" else (17, 29)):
            observed = {}
            for name, pair in pairs.items():
                if pair not in observed:
                    try:
                        observed[pair] = simulate(functions[pair], seed, 1 if mode == "contract" else 3, torch, np)
                    except InvalidOutput as error:
                        return {"status": "invalid" if mode == "contract" and name == "candidate" else "inconclusive",
                                "arm": name, "seed": seed, "issue": str(error)}
                stats = relative(observed[pairs["control"]], observed[pair], torch)
                results.append({"seed": seed, "arm": name, **stats})
    return {"status": "ok", "rows": results, "scope": "synthetic_cpu_raw_before_repair"}


if __name__ == "__main__":
    try:
        output = experiment(json.load(sys.stdin), sys.argv[1])
    except Exception as error:
        output = {"status": "inconclusive", "issue": "{}: {}".format(type(error).__name__, str(error)[:240])}
    print(json.dumps(output, allow_nan=False))

