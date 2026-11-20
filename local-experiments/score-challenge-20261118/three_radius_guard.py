# EVOLVE-BLOCK-START
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
    """Relative to the parent (random-walk contrastive loss only), add a
    timing-weighted star-edge attraction term
        sum_e w_e * softplus(-graph_scores_e) / sum_e w_e
    rescaled by (P+Q)/source_batch_size so its total gradient is comparable to
    the existing pair term and is strong enough to reorder groups at the
    area-balanced two-means boundary. Expected measurable effect: embeddings
    keep timing-heavy nets locally close, lowering the timing-weighted cut and
    shifting the official decoder's discrete top/bottom split, improving
    WNS/TNS. The hypothesis is invalidated if the final layer assignment is
    essentially unchanged or the timing-weighted cut does not fall.
    """
    pair_term = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    weight_total = graph_weights.sum()
    edge_mean = (graph_weights * F.softplus(-graph_scores)).sum() / (weight_total + 1e-6)
    pair_count = float(len(positive_scores)) + float(len(negative_scores))
    batch_scale = pair_count / max(1.0, float(source_batch_size))
    return pair_term + batch_scale * edge_mean


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Refine the parent partition with capacity-balanced rounding across supernode size bands."""
    n_nodes = int(embeddings.shape[0])
    total_area = node_areas.sum()
    mean_all = (node_areas[:, None] * embeddings).sum(axis=0) / max(float(total_area), 1e-12)

    anchor_index = int(seed) % max(1, n_nodes)
    anchor = embeddings[anchor_index]
    anchor_dist = ((embeddings - anchor) ** 2).sum(axis=1)
    far_index = int(np.argmax(anchor_dist))

    center_top = embeddings[far_index]
    center_bottom = embeddings[anchor_index]
    labels = np.where(np.arange(n_nodes) < max(1, n_nodes // 2), 1, 0)

    for iteration in range(max_iterations):
        dist_top = ((embeddings - center_top) ** 2).sum(axis=1)
        dist_bottom = ((embeddings - center_bottom) ** 2).sum(axis=1)
        score = dist_bottom - dist_top
        score_tie = score - (np.arange(n_nodes) * 1e-12)
        order = np.argsort(-score_tie)
        sorted_areas = node_areas[order]
        cumulative = np.cumsum(sorted_areas)
        target_area = balance_target * total_area
        errors = np.abs(cumulative - target_area)
        count = int(np.argmin(errors)) + 1
        count = max(1, min(n_nodes - 1, count))
        threshold = score_tie[order[count - 1]]
        labels = np.where(score_tie >= threshold, 1, 0)

        top_mask = labels == 1
        bottom_mask = labels == 0
        top_area = node_areas[top_mask].sum()
        bottom_area = node_areas[bottom_mask].sum()
        center_top = (
            node_areas[top_mask, None] * embeddings[top_mask]
        ).sum(axis=0) / max(float(top_area), 1e-12)
        center_bottom = (
            node_areas[bottom_mask, None] * embeddings[bottom_mask]
        ).sum(axis=0) / max(float(bottom_area), 1e-12)

    if max_iterations < 1 or n_nodes < 2:
        return labels

    # Trust geometric clustering only when the centers are at least three
    # pooled within-cluster RMS radii apart. Otherwise use capacity rounding.
    separation_sq = np.sum((center_top - center_bottom) ** 2)
    top_residual = ((embeddings[top_mask] - center_top) ** 2).sum(axis=1)
    bottom_residual = ((embeddings[bottom_mask] - center_bottom) ** 2).sum(axis=1)
    within = np.sum(node_areas[top_mask] * top_residual) + np.sum(node_areas[bottom_mask] * bottom_residual)
    pooled_radius_sq = within / total_area
    if separation_sq >= 9.0 * pooled_radius_sq:
        return labels

    log_areas = np.log(node_areas)
    # Pool capacity-granular items under one common preference order. Only
    # groups at least a total_area/sqrt(n_nodes) quantum receive size bands.
    quantum = total_area / np.sqrt(float(n_nodes))
    band = np.maximum(0, (1.0 + (log_areas - np.log(quantum)) / np.log(2.0)).astype(np.int64))
    band_order = np.lexsort((-score_tie, band))
    ordered_band = band[band_order]
    changes = ordered_band[1:] != ordered_band[:-1]
    starts = np.concatenate((np.zeros_like(band_order[:1]), np.arange(1, n_nodes)[changes]))
    ends = np.concatenate((starts[1:], np.ones_like(starts[:1]) * n_nodes))
    sizes = ends - starts
    band_index = np.cumsum(np.concatenate((np.ones_like(band_order[:1]), changes))) - 1
    band_areas = node_areas[band_order]
    prefix = np.concatenate((np.zeros_like(node_areas[:1]), np.cumsum(band_areas)))
    band_capacity = (prefix[ends] - prefix[starts]) * balance_target
    midpoint = prefix[:-1] - prefix[starts[band_index]] + 0.5 * band_areas
    preferred = midpoint <= band_capacity[band_index]
    # The most populated band supplies the final rounding capacity. Singleton
    # bands share a pool so their independent half-area targets do not all tie.
    reserve_band = int(np.argmax(sizes))
    reserve = band_index == reserve_band
    singleton = (sizes[band_index] == 1) & (band_index != reserve_band)
    fixed = preferred & (sizes[band_index] > 1) & (band_index != reserve_band)
    inverse = np.argsort(band_order)
    fixed_top = fixed[inverse]
    reserve_order = order[reserve[inverse][order]]
    singleton_order = order[singleton[inverse][order]]
    reserve_area = np.sum(node_areas[reserve_order])
    remainder = target_area - np.sum(node_areas[fixed_top])
    singleton_area = node_areas[singleton_order]
    desired = np.clip(balance_target * np.sum(singleton_area), max(0.0, remainder - reserve_area), max(0.0, remainder))
    singleton_prefix = np.concatenate((np.zeros_like(node_areas[:1]), np.cumsum(singleton_area)))
    take_singleton = int(np.argmin(np.abs(singleton_prefix - desired)))
    reserve_target = remainder - singleton_prefix[take_singleton]
    reserve_prefix = np.concatenate((np.zeros_like(node_areas[:1]), np.cumsum(node_areas[reserve_order])))
    take_reserve = int(np.argmin(np.abs(reserve_prefix - reserve_target)))
    fixed_order = order[fixed_top[order]]
    unpicked = order[(fixed_top[order] == 0) & (reserve[inverse][order] == 0) & (singleton[inverse][order] == 0)]
    top_count = len(fixed_order) + take_singleton + take_reserve
    if top_count == 0 or top_count == n_nodes:
        return labels
    rounded = np.concatenate((fixed_order, singleton_order[:take_singleton], reserve_order[:take_reserve],
                              unpicked, singleton_order[take_singleton:], reserve_order[take_reserve:]))
    proposed = (np.argsort(rounded) < top_count).astype(np.int64)
    return proposed
# EVOLVE-BLOCK-END
