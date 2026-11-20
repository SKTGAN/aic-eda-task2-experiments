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
    """Change versus parent: replace the frozen reference two-means call with a deterministic area-weighted variance-axis projection followed by a cumulative-area balanced sweep. Expected effect: supernodes can move across the area-balanced boundary that the raw weighted two-means kept fixed, changing the named assignment and timing-weighted cut. Invalidating result: partition diagnostics stay mostly unchanged or only die-swapped, or TNS regresses without a WNS gain."""
    total_area = np.sum(node_areas) + 1e-12
    weights = node_areas / total_area
    emb_mean = np.sum(embeddings * weights[:, None], axis=0)
    centered = embeddings - emb_mean
    variance = np.sum(centered * centered * weights[:, None], axis=0)
    var_order = np.argsort(variance)
    split_dim = var_order[-1]
    score = centered[:, split_dim]

    sort_order = np.argsort(score)
    sorted_areas = node_areas[sort_order]
    cum_area = np.cumsum(sorted_areas)
    target_area = float(balance_target) * total_area
    cut_count = int(np.sum(cum_area < target_area))
    cut_count = min(max(cut_count, 1), len(node_areas) - 1)

    ranks = np.argsort(sort_order)
    labels = np.where(ranks < cut_count, 1, 0)
    return labels
