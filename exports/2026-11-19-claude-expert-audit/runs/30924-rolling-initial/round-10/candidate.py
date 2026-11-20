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
    """Area-balanced adaptive-direction two-means decoder.
    Mechanism: center L2 embeddings, initialize the split axis at the physical-area-weighted maximum-variance coordinate, then alternate an area-cumulative projection split with area-weighted centroid updates for a bounded number of iterations; Decision: each iteration assigns whole supernodes to the top tier when their projection lies above the cumulative-area balance cut, changing the discrete partition rather than any loss term; Prediction: a cleaner global separation of graph-similar groups should reduce cross-tier timing-weighted connectivity and raise the mean bp-ng45 paired score versus the frozen reference decoder without a case-mean regression above 5 points; Falsifier: if the mean bp-ng45 paired score does not exceed the parent or any training case mean falls by more than 5 points, the mechanism is rejected.
    """
    emb_local = embeddings
    areas_local = node_areas
    total_area = areas_local.sum()
    mean_vec = (areas_local[:, None] * emb_local).sum(axis=0) / total_area
    centered = emb_local - mean_vec
    variances = (areas_local[:, None] * centered * centered).sum(axis=0)
    axis_idx = np.argmax(variances)
    projection = centered[:, axis_idx]

    order = np.argsort(projection)
    sorted_areas = areas_local[order]
    cumulative_area = np.cumsum(sorted_areas)
    threshold = balance_target * total_area
    threshold = max(threshold, sorted_areas[0])
    threshold = min(threshold, total_area - sorted_areas[len(sorted_areas) - 1])
    sorted_labels = np.where(cumulative_area <= threshold, 0, 1)
    labels_local = sorted_labels[np.argsort(order)]

    for iter_idx in range(max_iterations):
        top_mask = labels_local == 1
        bottom_mask = labels_local == 0
        top_area = (areas_local * top_mask).sum() + 1e-12
        bottom_area = (areas_local * bottom_mask).sum() + 1e-12
        top_center = (emb_local * (areas_local * top_mask)[:, None]).sum(axis=0) / top_area
        bottom_center = (emb_local * (areas_local * bottom_mask)[:, None]).sum(axis=0) / bottom_area
        direction = top_center - bottom_center
        projection = (centered * direction).sum(axis=1)

        order = np.argsort(projection)
        sorted_areas = areas_local[order]
        cumulative_area = np.cumsum(sorted_areas)
        threshold = balance_target * total_area
        threshold = max(threshold, sorted_areas[0])
        threshold = min(threshold, total_area - sorted_areas[len(sorted_areas) - 1])
        sorted_labels = np.where(cumulative_area <= threshold, 0, 1)
        labels_local = sorted_labels[np.argsort(order)]

    order = np.argsort(projection)
    sorted_areas = areas_local[order]
    cumulative_area = np.cumsum(sorted_areas)
    threshold = balance_target * total_area
    threshold = max(threshold, sorted_areas[0])
    threshold = min(threshold, total_area - sorted_areas[len(sorted_areas) - 1])
    sorted_labels = np.where(cumulative_area <= threshold, 0, 1)
    labels_local = sorted_labels[np.argsort(order)]
    return labels_local
