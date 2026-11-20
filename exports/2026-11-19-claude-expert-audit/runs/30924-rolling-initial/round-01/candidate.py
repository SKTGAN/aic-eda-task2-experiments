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
    """Mechanism: Euclidean area-weighted two-means projected onto the center-difference axis with an area-cumulative median split; Decision: assign dies by the signed projection threshold instead of spherical similarity to centers; Prediction: the area-balanced projection cut separates weakly timed groups differently from proposal A while keeping both dies populated; Falsifier: target-case paired timing does not improve or the final labels repeatedly collapse to one side."""
    total_area = np.sum(node_areas)
    eps = 1e-12
    node_count = len(node_areas)
    weighted_mean = np.sum(embeddings * node_areas[:, None], axis=0) / np.maximum(total_area, eps)
    mean_distance = np.sum((embeddings - weighted_mean) ** 2, axis=1)
    first = np.argmax(mean_distance)
    center_0 = embeddings[first]
    first_distance = np.sum((embeddings - center_0) ** 2, axis=1)
    second = np.argmax(first_distance)
    center_1 = embeddings[second]
    target = balance_target * total_area
    labels = np.where(np.arange(node_count) < np.maximum(1, node_count // 2), 0, 1)

    for step in range(max_iterations):
        direction = center_1 - center_0
        projection = np.sum(embeddings * direction, axis=1)
        order = np.argsort(projection)
        position = np.argsort(order)
        cumulative = np.cumsum(node_areas[order])
        labels = np.where(
            ((cumulative[position] <= target) | (position == 0)) & (position < node_count - 1),
            0,
            1,
        )
        weight_0 = node_areas * (labels == 0)
        weight_1 = node_areas * (labels == 1)
        sum_0 = np.sum(weight_0)
        sum_1 = np.sum(weight_1)
        new_0 = np.sum(embeddings * weight_0[:, None], axis=0) / np.maximum(sum_0, eps)
        new_1 = np.sum(embeddings * weight_1[:, None], axis=0) / np.maximum(sum_1, eps)
        center_0 = np.where(sum_0 > eps, new_0, center_0)
        center_1 = np.where(sum_1 > eps, new_1, center_1)

    direction = center_1 - center_0
    projection = np.sum(embeddings * direction, axis=1)
    order = np.argsort(projection)
    position = np.argsort(order)
    cumulative = np.cumsum(node_areas[order])
    labels = np.where(
        ((cumulative[position] <= target) | (position == 0)) & (position < node_count - 1),
        0,
        1,
    )
    return labels
