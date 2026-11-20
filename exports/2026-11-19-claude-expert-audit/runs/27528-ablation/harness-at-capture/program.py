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
    """Keep the parent loss behavior unchanged for this decoder-only trial.

    The positive/negative random-walk objective and the timing-weighted star-
    edge soft cut penalty are identical to the selected parent. The expected
    measurable effect comes only from the decoder change below. This loss
    hypothesis is invalidated if the decoder trial fails to move the official
    area-balanced partition or does not improve paired physical timing.
    """
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_denom = torch.clamp(graph_weights.sum(), min=1e-6)
    graph_penalty = (
        graph_weights * torch.sigmoid(graph_scores)
    ).sum() / graph_denom

    return pair_loss + 0.10 * graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Replace the parent helper call with one bounded custom area-balanced loop.

    Relative to the parent decoder, this keeps two-center area-weighted means
    but performs a fixed number of Lloyd-style refinements and rounds the
    embedding-distance ranking by cumulative physical area. The intended
    measurable effect is a more stable area-balanced boundary, so the protected
    closure moves fewer groups and TNS improves with WNS neutral. The hypothesis
    is invalidated if the official assignment is unchanged up to die swap or if
    paired combined score does not improve through TNS.
    """
    n_groups = len(node_areas)
    total_area = max(float(node_areas.sum()), 1e-12)
    first_index = int(abs(seed)) % max(n_groups, 1)
    first_dist = ((embeddings - embeddings[first_index]) ** 2).sum(axis=1)
    second_index = int(np.argmax(first_dist))
    if second_index == first_index:
        second_index = (first_index + 1) % max(n_groups, 1)

    center_zero = embeddings[first_index]
    center_one = embeddings[second_index]
    dist_zero = ((embeddings - center_zero) ** 2).sum(axis=1)
    dist_one = ((embeddings - center_one) ** 2).sum(axis=1)
    index_order = np.arange(n_groups)
    labels = np.where(
        index_order == 0,
        1,
        np.where(
            index_order == n_groups - 1,
            0,
            np.where(dist_one < dist_zero, 1, 0),
        ),
    )

    target_fraction = min(max(float(balance_target), 0.001), 0.999)
    target_area = target_fraction * total_area

    for iteration in range(max_iterations):
        dist_zero = ((embeddings - center_zero) ** 2).sum(axis=1)
        dist_one = ((embeddings - center_one) ** 2).sum(axis=1)
        preference = dist_zero - dist_one
        order = np.argsort(-preference)
        sorted_areas = node_areas[order]
        cumulative_before = np.cumsum(sorted_areas) - sorted_areas
        sorted_labels = np.where(
            (cumulative_before < target_area) & (np.arange(n_groups) < n_groups - 1),
            1,
            0,
        )
        labels = sorted_labels[np.argsort(order)]

        weights_zero = np.where(labels == 0, node_areas, 0.0)
        weights_one = np.where(labels == 1, node_areas, 0.0)
        denom_zero = max(float(weights_zero.sum()), 1e-12)
        denom_one = max(float(weights_one.sum()), 1e-12)
        center_zero = (embeddings * weights_zero[:, None]).sum(axis=0) / denom_zero
        center_one = (embeddings * weights_one[:, None]).sum(axis=0) / denom_one

    return labels.astype(np.int64)
