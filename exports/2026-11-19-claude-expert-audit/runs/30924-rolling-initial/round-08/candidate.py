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
    """Mechanism: deterministic area-balanced two-anchor Lloyd bisection on L2 embeddings; Decision: nodes above the cumulative-area split along the current area-weighted center-difference axis receive the top die; Prediction: a cleaner antipodal split reduces cross-tier timing-weighted connectivity and raises the bp-ng45 mean paired score versus the parent; Falsifier: bp-ng45 mean paired score does not exceed the parent, or any training case mean falls by more than its 5.0 tolerance."""
    n = embeddings.shape[0]
    total_area = max(float(node_areas.sum()), 1e-12)
    target_area = min(max(float(balance_target) * total_area, 1e-12), total_area - 1e-12)

    centered = embeddings - (
        embeddings * node_areas[:, None]
    ).sum(axis=0) / total_area
    radial = (centered * centered).sum(axis=1)
    anchor_top_index = int(np.argmax(radial))

    offset = embeddings - embeddings[anchor_top_index]
    far_sq = (offset * offset).sum(axis=1)
    anchor_bottom_index = int(np.argmax(far_sq))

    c_top = embeddings[anchor_top_index]
    c_bot = embeddings[anchor_bottom_index]
    labels = (np.arange(n) >= (n // 2)).astype(np.int64)

    for iteration in range(max_iterations):
        direction = c_top - c_bot
        denom = (direction * direction).sum()
        scores = np.where(
            denom > 1e-12,
            (embeddings * direction).sum(axis=1),
            centered[:, 0],
        )

        order = np.argsort(scores)
        sorted_areas = node_areas[order]
        cum = np.cumsum(sorted_areas)
        split_index = int(np.sum(cum < target_area))
        split_index = max(1, min(n - 1, split_index))

        rank = np.argsort(order)
        labels = (rank >= split_index).astype(np.int64)

        weights_top = node_areas * labels
        weights_bottom = node_areas * (1 - labels)
        sum_top = max(float(weights_top.sum()), 1e-12)
        sum_bottom = max(float(weights_bottom.sum()), 1e-12)

        c_top = (embeddings * weights_top[:, None]).sum(axis=0) / sum_top
        c_bot = (embeddings * weights_bottom[:, None]).sum(axis=0) / sum_bottom

    return labels
