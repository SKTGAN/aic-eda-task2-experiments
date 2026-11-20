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
    """Mechanism: area-weighted Euclidean two-means on L2 embeddings replaces spherical center normalization; Decision: choose each split by ranking the center-distance margin and cutting at the area-balanced cumulative quantile, with orientation inherited from the area-weighted variance direction; Prediction: bp_fe-ng45 mean paired score rises and most of its seeds improve versus R1 while bp-ng45 and ariane133-ng45 stay within the protected tolerances; Falsifier: bp_fe-ng45 mean paired delta is non-positive, or bp-ng45 mean falls below -5, or ariane133-ng45 mean falls below -37.246 versus R1."""
    unit_embedding = embeddings
    area_values = node_areas
    node_count = unit_embedding.shape[0]
    total_area = area_values.sum()
    area_scale = np.where(total_area > 0.0, total_area, 1.0)
    safe_balance = min(max(float(balance_target), 0.05), 0.95)
    target_low = area_scale * (1.0 - safe_balance)

    mean_embedding = (unit_embedding * area_values[:, None]).sum(axis=0) / area_scale
    centered_embedding = unit_embedding - mean_embedding
    weighted_variances = (centered_embedding * centered_embedding * area_values[:, None]).sum(axis=0)
    direction_index = int(np.argmax(weighted_variances))
    projection_values = centered_embedding[:, direction_index]

    order = np.argsort(projection_values)
    cumulative_area = np.cumsum(area_values[order])
    cut_index = int((cumulative_area < target_low).sum())
    cut_index = min(max(cut_index, 1), node_count - 1)
    rank_values = np.argsort(np.argsort(projection_values))
    tier_labels = (rank_values >= cut_index).astype(float)

    mask_top = tier_labels
    mask_bottom = 1.0 - tier_labels
    area_bottom = (area_values * mask_bottom).sum()
    area_top = (area_values * mask_top).sum()
    center_bottom = (unit_embedding * (area_values * mask_bottom)[:, None]).sum(axis=0) / np.where(area_bottom > 0.0, area_bottom, 1.0)
    center_top = (unit_embedding * (area_values * mask_top)[:, None]).sum(axis=0) / np.where(area_top > 0.0, area_top, 1.0)

    for iteration in range(max_iterations):
        center_delta = center_top - center_bottom
        center_offset = 0.5 * ((center_bottom * center_bottom).sum() - (center_top * center_top).sum())
        margin_score = (unit_embedding * center_delta).sum(axis=1) + center_offset

        order = np.argsort(margin_score)
        cumulative_area = np.cumsum(area_values[order])
        cut_index = int((cumulative_area < target_low).sum())
        cut_index = min(max(cut_index, 1), node_count - 1)
        rank_values = np.argsort(np.argsort(margin_score))
        tier_labels = (rank_values >= cut_index).astype(float)

        mask_top = tier_labels
        mask_bottom = 1.0 - tier_labels
        area_bottom = (area_values * mask_bottom).sum()
        area_top = (area_values * mask_top).sum()
        center_bottom = (unit_embedding * (area_values * mask_bottom)[:, None]).sum(axis=0) / np.where(area_bottom > 0.0, area_bottom, 1.0)
        center_top = (unit_embedding * (area_values * mask_top)[:, None]).sum(axis=0) / np.where(area_top > 0.0, area_top, 1.0)

    center_delta = center_top - center_bottom
    center_offset = 0.5 * ((center_bottom * center_bottom).sum() - (center_top * center_top).sum())
    margin_score = (unit_embedding * center_delta).sum(axis=1) + center_offset

    order = np.argsort(margin_score)
    cumulative_area = np.cumsum(area_values[order])
    cut_index = int((cumulative_area < target_low).sum())
    cut_index = min(max(cut_index, 1), node_count - 1)
    rank_values = np.argsort(np.argsort(margin_score))
    tier_labels = (rank_values >= cut_index).astype(int)
    return tier_labels
