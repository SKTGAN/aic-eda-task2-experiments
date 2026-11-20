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
    """Weight each sampled positive pair by the slack criticality of both ends.

    The timing signal rescales terms that already dominate the gradient instead
    of adding a small normalized term, so it can reorder groups at the
    area-balanced boundary. Expected effect: fewer critical paths cross dies,
    lower TNS deficit. Invalid if the decoder still reproduces the initial
    assignment, or if the timing-blind control below does as well.
    """
    slack = node_features[:, 0]
    covered = node_features[:, 6] > 0
    zero = torch.zeros_like(slack)
    count = torch.clamp(torch.where(covered, torch.ones_like(slack), zero).sum(), min=1.0)
    mean_slack = torch.where(covered, slack, zero).sum() / count
    centered = torch.where(covered, slack - mean_slack, zero)
    scale = torch.sqrt(torch.square(centered).sum() / count + 1e-12)
    critical = torch.where(covered, torch.sigmoid(-centered / scale), zero)
    pair_weight = 1.0 + 4.0 * critical[positive_sources] * critical[positive_targets]
    return -(
        (pair_weight * F.logsigmoid(positive_scores)).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
# EVOLVE-BLOCK-END
