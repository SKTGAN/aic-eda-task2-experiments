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
    """Unchanged from parent: maintained random-walk negative-sampling loss.

    This decoder-only edit leaves the loss mechanism and its behavior exactly
    as in the parent, so any measured timing change is attributable to the
    decoder. Expected effect: none from this function. Invalidation: a loss
    difference versus the parent would mean the decoder-only contract was
    violated.
    """
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Parent calls the frozen reference two-way decoder.

    Change: replace that single helper call with a custom bounded
    area-weighted two-center refinement. It initializes along the embedding
    coordinate with largest physical-area-weighted variance, splits by
    cumulative physical area at balance_target, then alternates weighted
    centers with a new area-cumsum-balanced projection split. The intended
    effect is to move supernodes across the area-balanced boundary, improving
    timing-weighted cut and TNS while keeping WNS near neutral. Invalidate if
    most cells keep the parent partition or if a case such as ariane133/1003
    shows TNS regression.
    """
    n = int(embeddings.shape[0])
    d = int(embeddings.shape[1])
    areas = node_areas
    total_area = float(np.sum(areas))
    mean = np.sum(embeddings * areas[:, None], axis=0) / total_area
    centered = embeddings - mean
    weighted_var = np.sum(centered * centered * areas[:, None], axis=0) / total_area
    best_dim = int(np.argmax(weighted_var))

    proj = centered[:, best_dim]
    order = np.argsort(proj)
    sorted_area = areas[order]
    cum = np.cumsum(sorted_area)
    target = balance_target * total_area
    split = int(np.argmax(cum >= target))
    if split <= 0:
        split = 1
    if split >= n:
        split = n - 1
    rank = np.cumsum(np.where(sorted_area > 0, 1.0, 0.0))
    sorted_labels = np.where(rank > split, 1, 0)
    labels = sorted_labels[np.argsort(order)]

    for iteration in range(max_iterations):
        bottom_mask = labels == 0
        top_mask = labels == 1
        bottom_area = float(np.sum(areas * bottom_mask))
        top_area = float(np.sum(areas * top_mask))
        bottom_area_safe = max(bottom_area, 1e-12)
        top_area_safe = max(top_area, 1e-12)
        c0 = np.sum(embeddings * (areas * bottom_mask)[:, None], axis=0) / bottom_area_safe
        c1 = np.sum(embeddings * (areas * top_mask)[:, None], axis=0) / top_area_safe
        diff = c1 - c0
        diff_norm2 = float(np.sum(diff * diff))
        if diff_norm2 <= 1e-20:
            proj = embeddings[:, best_dim]
        else:
            proj = np.sum(embeddings * diff, axis=1)

        order = np.argsort(proj)
        sorted_area = areas[order]
        cum = np.cumsum(sorted_area)
        target = balance_target * total_area
        split = int(np.argmax(cum >= target))
        if split <= 0:
            split = 1
        if split >= n:
            split = n - 1
        rank = np.cumsum(np.where(sorted_area > 0, 1.0, 0.0))
        sorted_labels = np.where(rank > split, 1, 0)
        labels = sorted_labels[np.argsort(order)]

    return labels
