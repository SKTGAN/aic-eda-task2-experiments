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
    """Parent loss preserved unchanged: exact random-walk pair logsigmoid objective.

    This candidate isolates the decoder mechanism, so the positive/negative
    sampled-pair objective remains identical to the parent. Expected effect:
    any timing change is attributable to the new discrete partition, not to a
    changed embedding objective. Falsifier: if the decoder partition is mostly
    unchanged, the loss path is not responsible for the result.
    """
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Area-balanced principal-axis split instead of seeded area-weighted two-means.

    Relative to the parent reference decoder, this uses deterministic power
    iteration on the area-weighted centered embedding covariance, then cuts
    the sorted projection by cumulative physical area. Expected measurable
    effect: a different discrete partition that moves whole groups across the
    area-balanced boundary, aiming to improve TNS without changing the loss.
    Falsifier: partition diagnostics remain mostly unchanged or timing
    regresses against the parent.
    """
    embedding_count = int(embeddings.shape[0])
    total_area = node_areas.sum()
    weighted_mean = (embeddings * node_areas[:, None]).sum(axis=0) / (total_area + 1e-12)
    centered = embeddings - weighted_mean[None, :]

    weighted_variance = (centered * centered * node_areas[:, None]).sum(axis=0)
    axis_index = int(np.argmax(weighted_variance))
    direction = centered[:, axis_index]
    direction_norm = np.sqrt((direction * direction).sum())
    direction = direction / (direction_norm + 1e-12)

    for step_index in range(max_iterations):
        projection = (centered * direction[None, :]).sum(axis=1)
        weighted_projection = node_areas * projection
        next_direction = (centered * weighted_projection[:, None]).sum(axis=0)
        next_norm = np.sqrt((next_direction * next_direction).sum())
        direction = next_direction / (next_norm + 1e-12)

    projection = (centered * direction[None, :]).sum(axis=1)
    order = np.argsort(projection)
    sorted_area = node_areas[order]
    cumulative_area = np.cumsum(sorted_area)

    target_share = max(0.05, min(0.95, float(balance_target)))
    target_bottom_area = (1.0 - target_share) * total_area
    raw_cut = int((cumulative_area < target_bottom_area).sum()) + 1
    cut_index = max(1, min(embedding_count - 1, raw_cut))

    rank = np.argsort(order)
    labels = (rank >= cut_index).astype(np.int64)
    return labels
