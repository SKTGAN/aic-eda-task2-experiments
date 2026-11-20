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
    """Keep the official random-walk embedding objective."""
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Place the area-balanced split at a clear gap in center preference."""
    initial = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    top_weights = node_areas * initial
    bottom_weights = node_areas * (1 - initial)
    top_center = np.sum(embeddings * top_weights[:, None], axis=0) / np.sum(top_weights)
    bottom_center = np.sum(embeddings * bottom_weights[:, None], axis=0) / np.sum(bottom_weights)

    preference = np.sum(embeddings * (top_center - bottom_center), axis=1)
    order = np.argsort(-preference, kind="stable")
    ranked = preference[order]
    gaps = ranked[:-1] - ranked[1:]
    area_error = np.abs(np.cumsum(node_areas[order])[:-1] / np.sum(node_areas) - balance_target)
    eligible = area_error <= 0.02
    if not np.any(eligible):
        return initial

    preferred_gaps = np.where(eligible, gaps, -1.0)
    split = 1 + int(np.lexsort((area_error, -preferred_gaps))[0])
    return (np.argsort(order) < split).astype(np.int64)
# EVOLVE-BLOCK-END
