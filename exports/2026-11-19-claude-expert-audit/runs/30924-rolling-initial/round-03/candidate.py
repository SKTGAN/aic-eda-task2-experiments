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
    """Mechanism: weight sampled logistic pairs by endpoint timing criticality from worst slack and coverage; Decision: critical groups dominate the embedding gradient so their pair assignments reshape the area-balanced two-way split; Prediction: timing-critical cross-die cuts fall and bp-ng45 mean paired score rises on most seeds; Falsifier: bp-ng45 mean paired score does not exceed the parent or a non-target case mean falls by more than its tolerance."""
    slack_raw = node_features[:, 0]
    coverage_raw = torch.clamp(node_features[:, 6], 0.0, 1.0)
    slack_filled = torch.where(
        torch.isfinite(slack_raw), slack_raw, torch.zeros_like(slack_raw)
    )
    coverage_filled = torch.where(
        torch.isfinite(coverage_raw), coverage_raw, torch.zeros_like(coverage_raw)
    )
    slack_scale = torch.mean(torch.abs(slack_filled)) + 1e-6
    criticality = torch.exp(
        -torch.clamp(slack_filled / slack_scale, -4.0, 4.0)
    ) * coverage_filled
    criticality_mean = torch.mean(criticality) + 1e-6
    node_importance = 0.5 + 0.5 * torch.clamp(
        criticality / criticality_mean, 0.0, 4.0
    )
    positive_weight = 0.5 * (
        node_importance[positive_sources] + node_importance[positive_targets]
    )
    negative_weight = 0.5 * (
        node_importance[negative_sources] + node_importance[negative_targets]
    )
    positive_loss = (
        positive_weight * F.logsigmoid(positive_scores)
    ).sum()
    negative_loss = (
        negative_weight * F.logsigmoid(-negative_scores)
    ).sum()
    return -(positive_loss + negative_loss) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
