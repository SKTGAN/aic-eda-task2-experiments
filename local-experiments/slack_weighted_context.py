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
    """Give more weight to positive pairs with negative average slack."""
    mean_slack = node_features[:, 1]
    timing_coverage = node_features[:, 6]
    timing_pressure = F.relu(-mean_slack) * timing_coverage
    pair_pressure = timing_pressure[positive_sources] + timing_pressure[positive_targets]
    relative_pressure = pair_pressure / pair_pressure.mean().clamp_min(1e-12)
    pair_weights = 1.0 + relative_pressure / (1.0 + relative_pressure)
    pair_weights = pair_weights / pair_weights.mean()

    positive_loss = -(pair_weights * F.logsigmoid(positive_scores)).sum()
    negative_loss = -F.logsigmoid(-negative_scores).sum()
    return (positive_loss + negative_loss) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Use the area-balanced decoder from the initial algorithm."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
# EVOLVE-BLOCK-END
