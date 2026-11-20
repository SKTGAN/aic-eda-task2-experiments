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
    """Mechanism: retain the random-walk contrastive loss and add a timing-weighted graph-star attraction term over supplied graph edges; Decision: the embedding geometry is pulled toward positive L2 dot products on high-weight net edges, giving timing-critical connected groups a lower cut cost before the frozen area-balanced two-means decoder assigns tiers; Prediction: matched-case combined timing should improve where timing-weighted cuts are reduced, with labels changing near decoder decision boundaries rather than by case- or seed-specific rules; Falsifier: matched-case combined score fails to improve while timing-weighted cut and decoder assignments remain unchanged."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    graph_weight_total = torch.clamp(graph_weights.sum(), min=1e-6)
    graph_star_loss = (
        graph_weights * F.softplus(-graph_scores)
    ).sum() / graph_weight_total
    return pair_loss + 0.75 * graph_star_loss


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Mechanism: preserve the frozen seeded area-balanced two-means handoff, then apply bidirectional high-margin wrong-side micro-flips with independent per-direction area and count caps; Decision: a group changes tier only when it is closer to the opposite area-weighted center, and top-to-bottom and bottom-to-top moves are budgeted separately so one direction cannot consume the whole movement budget; Prediction: timing-weighted cut and combined score should improve where the parent one-sided micro-flip left boundary groups unbalanced, with smaller cross-seed regressions than a single shared movement cap; Falsifier: matched official combined score fails to improve while the selected bidirectional flips are present or the timing-weighted cut does not fall."""
    labels = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    areas = np.maximum(node_areas, 1e-12)
    total_area = np.sum(areas)
    top_mask = labels == 1
    bottom_mask = labels == 0
    top_area = np.sum(areas * top_mask)
    bottom_area = np.sum(areas * bottom_mask)
    top_center = np.sum(embeddings * (areas * top_mask)[:, None], axis=0) / np.maximum(top_area, 1e-12)
    bottom_center = np.sum(embeddings * (areas * bottom_mask)[:, None], axis=0) / np.maximum(bottom_area, 1e-12)
    d_top = np.sum((embeddings - top_center) ** 2, axis=1)
    d_bottom = np.sum((embeddings - bottom_center) ** 2, axis=1)
    margin = d_bottom - d_top
    violation = np.where(labels == 1, -margin, margin)
    candidate = violation > 0.0
    priority = np.where(candidate, violation / areas, -1.0)

    down_mask = candidate & (labels == 1)
    up_mask = candidate & (labels == 0)
    max_move_area_dir = 0.0015 * total_area
    max_count_dir = max(1, int(0.0015 * labels.size))

    order_down = np.argsort(-np.where(down_mask, priority, -1.0))
    sorted_down = down_mask[order_down]
    sorted_areas_down = areas[order_down]
    cum_area_down = np.cumsum(np.where(sorted_down, sorted_areas_down, 0.0))
    cum_count_down = np.cumsum(sorted_down)
    selected_down_sorted = sorted_down & (cum_area_down <= max_move_area_dir) & (cum_count_down <= max_count_dir)
    selected_down = selected_down_sorted[np.argsort(order_down)]

    order_up = np.argsort(-np.where(up_mask, priority, -1.0))
    sorted_up = up_mask[order_up]
    sorted_areas_up = areas[order_up]
    cum_area_up = np.cumsum(np.where(sorted_up, sorted_areas_up, 0.0))
    cum_count_up = np.cumsum(sorted_up)
    selected_up_sorted = sorted_up & (cum_area_up <= max_move_area_dir) & (cum_count_up <= max_count_dir)
    selected_up = selected_up_sorted[np.argsort(order_up)]

    selected = selected_down | selected_up
    new_labels = np.where(selected, 1 - labels, labels)
    top_count = np.sum(new_labels == 1)
    bottom_count = labels.size - top_count
    if top_count == 0 or bottom_count == 0:
        return labels
    return new_labels
