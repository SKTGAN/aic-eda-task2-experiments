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
    """Mechanism: retain the random-walk contrastive pair loss and the timing-weighted graph-star attraction term, but sharpen graph-edge weights to the cubic power of the supplied timing weights; Decision: superlinearly emphasize the highest-weight timing-critical net-star edges in the embedding gradient while leaving the pair loss, graph normalization, graph coefficient, and decoder unchanged; Prediction: timing-weighted cut should fall and matched official combined timing should improve across cases and seeds, especially where moderate-weight attraction previously diluted the most timing-critical edges; Falsifier: matched official combined score fails to improve while decoder assignments and timing-weighted cut remain unchanged."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    graph_weight_pos = torch.clamp(graph_weights, min=0.0)
    graph_weight_cu = torch.square(graph_weight_pos) * graph_weight_pos
    graph_weight_total = torch.clamp(graph_weight_cu.sum(), min=1e-12)
    graph_star_loss = (
        graph_weight_cu * F.softplus(-graph_scores)
    ).sum() / graph_weight_total
    return pair_loss + 0.75 * graph_star_loss


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Mechanism: preserve the frozen seeded area-balanced two-means handoff, then apply only area-corrective bounded wrong-side micro-flips toward the physical-area target; Decision: a group changes tier only when it is closer to the opposite area-weighted center and the move goes from the currently overfull side toward the underfull side, with the same small area and count caps; Prediction: timing-weighted cut should remain low while area-balance repair movement and the largest cross-seed regressions shrink, improving matched combined timing over the parent; Falsifier: matched official combined score fails to improve while selected flips are present or area-balance repair movement does not fall."""
    base_labels = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    areas_eff = np.maximum(node_areas, 1e-12)
    total_area = np.sum(areas_eff)
    top_mask = base_labels == 1
    bottom_mask = base_labels == 0
    top_area = np.sum(areas_eff * top_mask)
    bottom_area = np.sum(areas_eff * bottom_mask)
    top_center = np.sum(embeddings * (areas_eff * top_mask)[:, None], axis=0) / np.maximum(top_area, 1e-12)
    bottom_center = np.sum(embeddings * (areas_eff * bottom_mask)[:, None], axis=0) / np.maximum(bottom_area, 1e-12)
    d_top = np.sum((embeddings - top_center) ** 2, axis=1)
    d_bottom = np.sum((embeddings - bottom_center) ** 2, axis=1)
    margin = d_bottom - d_top
    violation = np.where(base_labels == 1, -margin, margin)
    top_share = top_area / np.maximum(total_area, 1e-12)
    move_top_to_bottom = top_share > balance_target
    candidate = np.where(
        move_top_to_bottom,
        (base_labels == 1) & (violation > 0.0),
        (base_labels == 0) & (violation > 0.0),
    )
    priority = np.where(candidate, violation / areas_eff, -1.0)
    order = np.argsort(-priority)
    sorted_candidate = candidate[order]
    sorted_areas = areas_eff[order]
    move_areas = np.where(sorted_candidate, sorted_areas, 0.0)
    cum_move_area = np.cumsum(move_areas)
    cum_count = np.cumsum(sorted_candidate)
    max_move_area = 0.002 * total_area
    max_count = max(1, int(0.002 * base_labels.size))
    selected_sorted = sorted_candidate & (cum_move_area <= max_move_area) & (cum_count <= max_count)
    selected = selected_sorted[np.argsort(order)]
    new_labels = np.where(selected, 1 - base_labels, base_labels)
    top_count = np.sum(new_labels == 1)
    bottom_count = new_labels.size - top_count
    if top_count == 0 or bottom_count == 0:
        return base_labels
    return new_labels
