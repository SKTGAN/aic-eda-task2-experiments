# EVOLVE-BLOCK-START
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
    """Timing-blind control: give every sampled positive pair the same mean weight.

    Uses the same statistics and the same average multiplier as the
    criticality-weighted loss, but spreads it uniformly. Any difference between
    the two candidates is then due to which pairs carry the weight.
    """
    slack = node_features[:, 0]
    covered = node_features[:, 6] > 0
    zero = torch.zeros_like(slack)
    count = torch.clamp(torch.where(covered, torch.ones_like(slack), zero).sum(), min=1.0)
    mean_slack = torch.where(covered, slack, zero).sum() / count
    centered = torch.where(covered, slack - mean_slack, zero)
    scale = torch.sqrt(torch.square(centered).sum() / count + 1e-12)
    critical = torch.where(covered, torch.sigmoid(-centered / scale), zero)
    pair_weight = 1.0 + 4.0 * (critical[positive_sources] * critical[positive_targets]).mean()
    return -(
        (pair_weight * F.logsigmoid(positive_scores)).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
# EVOLVE-BLOCK-END
