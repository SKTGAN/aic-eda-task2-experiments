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
    """Mechanism: replace Euclidean area-weighted two-means with area-balanced spherical k-means that recomputes area-weighted cosine centers and cuts the cosine margin at the cumulative-area balance quantile; Decision: a node whose cosine margin rank is at or above the area-cumulative split is placed in the top tier; Prediction: timing-critical cross-tier edges decrease and the bp-ng45 mean paired score rises on most seeds versus the parent; Falsifier: bp-ng45 mean paired score does not exceed the parent or another training case mean falls by more than its tolerance."""
    n = int(embeddings.shape[0])
    total_area = float(np.sum(node_areas))
    if n < 2 or total_area <= 0.0:
        cut = max(1, n // 2)
        return np.where(np.arange(n) < cut, 1, 0)

    weighted_mean = np.sum(embeddings * node_areas[:, None], axis=0) / total_area
    centered = embeddings - weighted_mean
    axis_variances = np.sum(node_areas[:, None] * centered * centered, axis=0) / total_area
    axis = int(np.argmax(axis_variances))
    projection = centered[:, axis]
    order0 = np.argsort(projection)
    ranks0 = np.argsort(order0)
    cumulative0 = np.cumsum(node_areas[order0])
    target0 = total_area * float(balance_target)
    split0 = int(np.sum(cumulative0 < target0))
    split0 = max(1, min(n - 1, split0))
    labels = np.where(ranks0 >= split0, 1, 0)

    for iteration in range(max_iterations):
        top_mask = labels == 1
        bottom_mask = labels == 0
        top_area = float(np.sum(node_areas[top_mask]))
        bottom_area = float(np.sum(node_areas[bottom_mask]))
        top_center = np.sum(embeddings[top_mask] * node_areas[top_mask][:, None], axis=0) / (top_area + 1e-12)
        bottom_center = np.sum(embeddings[bottom_mask] * node_areas[bottom_mask][:, None], axis=0) / (bottom_area + 1e-12)
        top_norm = np.sqrt(np.sum(top_center * top_center)) + 1e-12
        bottom_norm = np.sqrt(np.sum(bottom_center * bottom_center)) + 1e-12
        top_similarity = np.sum(embeddings * (top_center / top_norm), axis=1)
        bottom_similarity = np.sum(embeddings * (bottom_center / bottom_norm), axis=1)
        margin = top_similarity - bottom_similarity
        margin_order = np.argsort(margin)
        margin_ranks = np.argsort(margin_order)
        cumulative = np.cumsum(node_areas[margin_order])
        target = total_area * float(balance_target)
        split = int(np.sum(cumulative < target))
        split = max(1, min(n - 1, split))
        new_labels = np.where(margin_ranks >= split, 1, 0)
        changed = int(np.sum(new_labels != labels))
        labels = new_labels
        if changed == 0:
            break

    return labels
