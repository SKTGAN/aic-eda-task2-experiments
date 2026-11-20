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
    """Unchanged from the parent: maintain the random-walk pair objective so the decoder change is isolated."""
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Replace the parent decoder with one bounded area-weighted two-means loop whose final split uses a deterministic affinity-margin ordering plus cumulative physical area rather than nearest-center rounding. This should move whole groups across the area-balanced boundary where the nearest-center tie or margin is weak. The hypothesis is invalidated if the returned labels are rejected, if both die sides are not nonempty, or if matched-case mean timing does not improve over the parent."""
    count_nodes = embeddings.shape[0]
    count_dims = embeddings.shape[1]
    total_area = np.sum(node_areas) + 1e-12

    weighted_mean = np.sum(embeddings * node_areas[:, None], axis=0) / total_area
    centered = embeddings - weighted_mean
    weighted_variance = np.sum(centered * centered * node_areas[:, None], axis=0) / total_area
    split_dim = np.argmax(weighted_variance)
    direction = (np.arange(count_dims) == split_dim) * 1.0
    spread = np.sqrt(weighted_variance[split_dim]) + 1e-12

    center_top = weighted_mean + spread * direction
    center_bottom = weighted_mean - spread * direction

    for step in range(max_iterations):
        dist_top = np.sum((embeddings - center_top) ** 2, axis=1)
        dist_bottom = np.sum((embeddings - center_bottom) ** 2, axis=1)
        margin = dist_bottom - dist_top
        order = np.argsort(-margin)
        sorted_areas = node_areas[order]
        cumulative = np.cumsum(sorted_areas)
        count_top = np.sum(cumulative < balance_target * total_area)
        count_top = np.clip(count_top, 1, count_nodes - 1)
        rank = np.argsort(order)
        top_mask = np.where(rank < count_top, 1, 0)

        area_top = np.sum(node_areas * top_mask)
        area_bottom = np.sum(node_areas * (1 - top_mask))
        center_top = np.sum(embeddings * (node_areas * top_mask)[:, None], axis=0) / (area_top + 1e-12)
        center_bottom = np.sum(embeddings * (node_areas * (1 - top_mask))[:, None], axis=0) / (area_bottom + 1e-12)

    dist_top = np.sum((embeddings - center_top) ** 2, axis=1)
    dist_bottom = np.sum((embeddings - center_bottom) ** 2, axis=1)
    margin = dist_bottom - dist_top
    order = np.argsort(-margin)
    sorted_areas = node_areas[order]
    cumulative = np.cumsum(sorted_areas)
    count_top = np.sum(cumulative < balance_target * total_area)
    count_top = np.clip(count_top, 1, count_nodes - 1)
    rank = np.argsort(order)
    labels = np.where(rank < count_top, 1, 0)
    return labels
