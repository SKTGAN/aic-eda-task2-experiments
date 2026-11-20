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
    """Deterministic area-balanced two-means decoder.

    Change: replace the seeded reference clustering with a custom bounded loop
    that initializes centers from weighted-mean extreme embeddings and applies
    cumulative-area balancing before each physical-area-weighted center update.
    Expected measurable effect: a more stable handoff partition across seeds and
    designs, with fewer closure-driven label movements that can disturb timing.
    Against: if official WNS/TNS do not improve or the final assignment and
    closure movement match the parent, this mechanism is unsupported.
    """
    emb = embeddings
    areas = node_areas
    node_count = emb.shape[0]
    total_area = areas.sum()
    safe_total = max(float(total_area), 1e-12)
    target_share = min(max(float(balance_target), 0.03), 0.97)
    target_area = target_share * safe_total

    mean_vec = (emb * areas[:, None]).sum(axis=0) / safe_total
    mean_delta = emb - mean_vec
    mean_dist = np.sum(mean_delta * mean_delta, axis=1)
    first_idx = int(np.argmax(mean_dist))
    first_vec = emb[first_idx]
    first_delta = emb - first_vec
    first_dist = np.sum(first_delta * first_delta, axis=1)
    second_idx = int(np.argmax(first_dist))
    if second_idx == first_idx:
        second_idx = (first_idx + 1) % node_count

    center_top = emb[first_idx]
    center_bottom = emb[second_idx]
    labels = (np.sum((emb - center_top) * (emb - center_top), axis=1)
              <= np.sum((emb - center_bottom) * (emb - center_bottom), axis=1)) * 1

    for iteration in range(max_iterations):
        top_delta = emb - center_top
        bottom_delta = emb - center_bottom
        dist_top = np.sum(top_delta * top_delta, axis=1)
        dist_bottom = np.sum(bottom_delta * bottom_delta, axis=1)
        preference = dist_bottom - dist_top
        order = np.argsort(-preference)
        sorted_areas = areas[order]
        cumulative_area = np.cumsum(sorted_areas)
        split_pos = int(np.argmax(cumulative_area >= target_area)) + 1
        split_pos = min(max(split_pos, 1), node_count - 1)
        rank = np.argsort(order)
        labels = (rank < split_pos) * 1

        top_mask = labels > 0
        bottom_mask = labels < 1
        top_area = areas[top_mask].sum()
        bottom_area = areas[bottom_mask].sum()
        top_weight = areas * top_mask
        bottom_weight = areas * bottom_mask
        center_top = (emb * top_weight[:, None]).sum(axis=0) / max(float(top_area), 1e-12)
        center_bottom = (emb * bottom_weight[:, None]).sum(axis=0) / max(float(bottom_area), 1e-12)

    return labels
