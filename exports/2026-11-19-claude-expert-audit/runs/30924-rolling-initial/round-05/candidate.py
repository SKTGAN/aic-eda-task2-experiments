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
    """Mechanism: add a criticality-sharpened hinge attraction over timing-weighted star edges beside the random-walk logistic objective; Decision: the hinge gradient on a graph edge sets which endpoint embeddings move together, changing the top-tier membership produced by the unchanged area-balanced two-means decoder; Prediction: timing-critical cross-tier cuts fall and the bp-ng45 mean paired score rises on most seeds versus the parent; Falsifier: bp-ng45 mean paired score does not exceed the parent or another training case mean falls by more than its tolerance."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    edge_cos = torch.where(
        torch.isfinite(graph_scores),
        graph_scores,
        torch.zeros_like(graph_scores),
    )
    edge_w = torch.clamp(
        torch.where(
            torch.isfinite(graph_weights),
            graph_weights,
            torch.zeros_like(graph_weights),
        ),
        min=0.0,
    )
    edge_mean = edge_w.sum() / max(1, len(graph_weights))
    edge_scale = torch.clamp(edge_mean, min=1e-6)
    edge_focus = torch.clamp(torch.square(edge_w / edge_scale), max=20.0)
    edge_norm = torch.clamp(edge_focus.sum(), min=1e-6)
    edge_penalty = (edge_focus * F.relu(0.5 - edge_cos)).sum() / edge_norm

    area_total = torch.clamp(node_areas.sum(), min=1e-6)
    area_center = (node_areas[:, None] * embeddings).sum(dim=0) / area_total
    centered = embeddings - area_center
    spread = (
        node_areas * torch.sum(torch.square(centered), dim=1)
    ).sum() / area_total
    spread_floor = F.relu(0.2 - spread)

    progress = float(epoch) / float(max(1, max_epochs))
    edge_weight = 0.5 + 0.5 * progress
    return pair_loss + edge_weight * edge_penalty + 0.1 * spread_floor


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
