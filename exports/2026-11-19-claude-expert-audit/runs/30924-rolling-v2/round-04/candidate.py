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
    """Mechanism: add an angular-margin correction to the maintained random-walk pair objective; Decision: raise loss when positive dot products fall below a margin and when sampled negative dot products exceed a negative margin; Prediction: the sharper pair geometry changes the embedding partition and raises the target case's mean paired score while other case means stay within the stated tolerance; Falsifier: target-case mean paired delta is non-positive against the parent, or any non-target case mean falls more than 5 points below the parent."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    positive_margin = 0.35
    negative_margin = 0.20
    positive_penalty = F.relu(positive_margin - positive_scores).sum() / max(1, len(positive_scores))
    negative_penalty = F.relu(negative_scores + negative_margin).sum() / max(1, len(negative_scores))

    return pair_loss + 0.25 * positive_penalty + 0.50 * negative_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Mechanism: replace Euclidean nearest-center rounding with area-cumulative spherical two-means on L2 embeddings; Decision: choose each split by ranking a cosine-score projection and cutting at the area-balanced cumulative quantile; Prediction: bp-ng45 mean paired score rises and most of its seeds improve versus the parent while other case means stay within tolerance; Falsifier: bp-ng45 mean paired delta is non-positive or any case mean falls more than 5 below the parent."""
    n = embeddings.shape[0]
    total_area = node_areas.sum()
    area_scale = np.where(total_area > 0.0, total_area, 1.0)
    safe_balance = min(max(float(balance_target), 0.05), 0.95)
    target_low = area_scale * (1.0 - safe_balance)

    mean_embedding = (embeddings * node_areas[:, None]).sum(axis=0) / area_scale
    centered = embeddings - mean_embedding
    variances = (centered * centered * node_areas[:, None]).sum(axis=0)
    direction_index = int(np.argmax(variances))
    projection = centered[:, direction_index]

    order = np.argsort(projection)
    cumulative = np.cumsum(node_areas[order])
    cut = int((cumulative < target_low).sum())
    cut = min(max(cut, 1), n - 1)
    ranks = np.argsort(np.argsort(projection))
    labels = (ranks >= cut).astype(float)

    mask1 = labels
    mask0 = 1.0 - labels
    area0 = (node_areas * mask0).sum()
    area1 = (node_areas * mask1).sum()
    center0 = (embeddings * (node_areas * mask0)[:, None]).sum(axis=0) / np.where(area0 > 0.0, area0, 1.0)
    center1 = (embeddings * (node_areas * mask1)[:, None]).sum(axis=0) / np.where(area1 > 0.0, area1, 1.0)
    center0 = center0 / (np.sqrt((center0 * center0).sum()) + 1e-12)
    center1 = center1 / (np.sqrt((center1 * center1).sum()) + 1e-12)

    for iteration in range(max_iterations):
        score = (embeddings * (center1 - center0)).sum(axis=1)
        order = np.argsort(score)
        cumulative = np.cumsum(node_areas[order])
        cut = int((cumulative < target_low).sum())
        cut = min(max(cut, 1), n - 1)
        ranks = np.argsort(np.argsort(score))
        labels = (ranks >= cut).astype(float)

        mask1 = labels
        mask0 = 1.0 - labels
        area0 = (node_areas * mask0).sum()
        area1 = (node_areas * mask1).sum()
        center0 = (embeddings * (node_areas * mask0)[:, None]).sum(axis=0) / np.where(area0 > 0.0, area0, 1.0)
        center1 = (embeddings * (node_areas * mask1)[:, None]).sum(axis=0) / np.where(area1 > 0.0, area1, 1.0)
        center0 = center0 / (np.sqrt((center0 * center0).sum()) + 1e-12)
        center1 = center1 / (np.sqrt((center1 * center1).sum()) + 1e-12)

    score = (embeddings * (center1 - center0)).sum(axis=1)
    order = np.argsort(score)
    cumulative = np.cumsum(node_areas[order])
    cut = int((cumulative < target_low).sum())
    cut = min(max(cut, 1), n - 1)
    ranks = np.argsort(np.argsort(score))
    labels = (ranks >= cut).astype(int)
    return labels
