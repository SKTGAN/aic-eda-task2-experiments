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
    """Mechanism: keep the area-balanced two-center refinement but re-rank every node by a diagonal-LDA (pooled within-tier variance normalized) embedding score instead of the raw center-difference projection; Decision: the tier boundary is placed by the unchanged area-cumulative quantile on the whitened score, so low-variance embedding directions that the raw projection buried can move nodes across the cut; Prediction: versus R1 the bp_fe-ng45 mean paired score delta is positive with at least two of its three seeds improving, while bp-ng45 and ariane133-ng45 case means stay within 5 points of R1; Falsifier: bp_fe-ng45 mean paired delta is non-positive versus R1, or any case mean falls more than 5 points below R1."""
    n = embeddings.shape[0]
    total_area = node_areas.sum()
    area_total = np.where(total_area > 0.0, total_area, 1.0)
    safe_balance = min(max(float(balance_target), 0.05), 0.95)
    bottom_target = area_total * (1.0 - safe_balance)

    mean_vec = (embeddings * node_areas[:, None]).sum(axis=0) / area_total
    centered = embeddings - mean_vec
    spread = (centered * centered * node_areas[:, None]).sum(axis=0) / area_total
    axis = int(np.argmax(spread))
    score = centered[:, axis]

    for iteration in range(max_iterations):
        order = np.argsort(score)
        cumulative = np.cumsum(node_areas[order])
        cut = int((cumulative < bottom_target).sum())
        cut = min(max(cut, 1), n - 1)
        ranks = np.argsort(np.argsort(score))
        labels = (ranks >= cut).astype(float)

        mask_top = labels
        mask_bottom = 1.0 - labels
        weight_top = node_areas * mask_top
        weight_bottom = node_areas * mask_bottom
        area_top = weight_top.sum()
        area_bottom = weight_bottom.sum()
        center_top = (embeddings * weight_top[:, None]).sum(axis=0) / np.where(area_top > 0.0, area_top, 1.0)
        center_bottom = (embeddings * weight_bottom[:, None]).sum(axis=0) / np.where(area_bottom > 0.0, area_bottom, 1.0)
        gap = center_top - center_bottom

        dev_top = embeddings - center_top
        dev_bottom = embeddings - center_bottom
        var_top = (dev_top * dev_top * weight_top[:, None]).sum(axis=0) / np.where(area_top > 0.0, area_top, 1.0)
        var_bottom = (dev_bottom * dev_bottom * weight_bottom[:, None]).sum(axis=0) / np.where(area_bottom > 0.0, area_bottom, 1.0)
        pooled = (area_bottom * var_bottom + area_top * var_top) / area_total
        floor = 0.01 * pooled.mean() + 1e-12
        scale = gap / np.sqrt(pooled + floor)
        score = (embeddings * scale[None, :]).sum(axis=1)

    order = np.argsort(score)
    cumulative = np.cumsum(node_areas[order])
    cut = int((cumulative < bottom_target).sum())
    cut = min(max(cut, 1), n - 1)
    ranks = np.argsort(np.argsort(score))
    labels = (ranks >= cut).astype(int)
    return labels
