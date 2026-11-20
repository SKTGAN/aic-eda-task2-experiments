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
    """Mechanism: keep the frozen random-walk logistic objective and add a timing-criticality-scaled softplus attraction over supplied timing-context star edges; Decision: high-criticality graph edges receive a larger similarity margin, which moves the unchanged area-balanced decoder toward keeping their endpoints in the same tier instead of splitting them; Prediction: the bp-ng45 mean paired score rises versus the parent on most seeds, with other case means staying within tolerance; Falsifier: bp-ng45 mean paired score does not exceed the parent, or any training case mean falls by more than 5.0 points."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    slack = node_features[:, 0]
    coverage = node_features[:, 6]
    finite_slack = torch.where(
        torch.isfinite(slack), slack, torch.zeros_like(slack)
    )
    finite_coverage = torch.where(
        torch.isfinite(coverage), coverage, torch.zeros_like(coverage)
    )
    slack_scale = torch.mean(torch.abs(finite_slack)) + 1e-3
    raw_criticality = torch.sigmoid(-finite_slack / slack_scale)
    safe_criticality = torch.where(
        torch.isfinite(raw_criticality),
        raw_criticality,
        torch.zeros_like(raw_criticality),
    )
    node_criticality = torch.where(
        finite_coverage > 0,
        safe_criticality,
        torch.zeros_like(safe_criticality),
    )

    source_criticality = node_criticality[graph_sources]
    target_criticality = node_criticality[graph_targets]
    edge_criticality = 0.5 * (source_criticality + target_criticality)
    graph_margin = 0.25 + 0.75 * edge_criticality
    graph_term = torch.sum(
        graph_weights
        * edge_criticality
        * F.softplus(graph_margin - graph_scores)
    )
    graph_denominator = torch.sum(graph_weights * edge_criticality) + 1.0
    graph_loss = graph_term / graph_denominator

    return pair_loss + 0.35 * graph_loss


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
