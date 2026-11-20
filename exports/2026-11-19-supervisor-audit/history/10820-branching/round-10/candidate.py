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
    """Mechanism: retain the random-walk contrastive loss and the timing-weighted graph-star attraction term, but renormalize graph edges by squared timing weights; Decision: emphasize high-weight timing-critical net-star edges in the embedding gradient while leaving the decoder and all non-graph loss terms unchanged, so the tier decision near decoder boundaries is driven more by timing-critical connections; Prediction: timing-weighted cut should fall and matched-case combined timing should improve across cases and seeds with smaller cross-seed regression than linear edge weighting; Falsifier: matched official combined score fails to improve while decoder assignments and timing-weighted cut remain unchanged."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    graph_weight_pos = torch.clamp(graph_weights, min=0.0)
    graph_weight_sq = torch.square(graph_weight_pos)
    graph_weight_total = torch.clamp(graph_weight_sq.sum(), min=1e-12)
    graph_star_loss = (
        graph_weight_sq * F.softplus(-graph_scores)
    ).sum() / graph_weight_total
    return pair_loss + 0.75 * graph_star_loss


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Mechanism: preserve the frozen seeded area-balanced two-means handoff, then apply two bounded area-corrective wrong-side micro-flip passes with recentered area-weighted centers after the first pass; Decision: a group changes tier on each pass only when it is closer to the opposite recentered center and the move goes from the currently overfull side toward the underfull side, with a smaller second-pass area and count budget; Prediction: timing-weighted cut should fall further and matched combined timing should improve across more cases and seeds than the single-pass parent while preserving its prior gain; Falsifier: matched official combined score fails to improve over the parent while second-pass selected flips are present or timing-weighted cut does not fall."""
    base_labels = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    areas_eff = np.maximum(node_areas, 1e-12)
    total_area = np.sum(areas_eff)

    top_mask_1 = base_labels == 1
    bottom_mask_1 = base_labels == 0
    top_area_1 = np.sum(areas_eff * top_mask_1)
    bottom_area_1 = np.sum(areas_eff * bottom_mask_1)
    top_center_1 = np.sum(embeddings * (areas_eff * top_mask_1)[:, None], axis=0) / np.maximum(top_area_1, 1e-12)
    bottom_center_1 = np.sum(embeddings * (areas_eff * bottom_mask_1)[:, None], axis=0) / np.maximum(bottom_area_1, 1e-12)
    d_top_1 = np.sum((embeddings - top_center_1) ** 2, axis=1)
    d_bottom_1 = np.sum((embeddings - bottom_center_1) ** 2, axis=1)
    margin_1 = d_bottom_1 - d_top_1
    violation_1 = np.where(base_labels == 1, -margin_1, margin_1)
    top_share_1 = top_area_1 / np.maximum(total_area, 1e-12)
    move_top_to_bottom_1 = top_share_1 > balance_target
    candidate_1 = np.where(
        move_top_to_bottom_1,
        (base_labels == 1) & (violation_1 > 0.0),
        (base_labels == 0) & (violation_1 > 0.0),
    )
    priority_1 = np.where(candidate_1, violation_1 / areas_eff, -1.0)
    order_1 = np.argsort(-priority_1)
    sorted_candidate_1 = candidate_1[order_1]
    sorted_areas_1 = areas_eff[order_1]
    move_areas_1 = np.where(sorted_candidate_1, sorted_areas_1, 0.0)
    cum_move_area_1 = np.cumsum(move_areas_1)
    cum_count_1 = np.cumsum(sorted_candidate_1)
    max_move_area_1 = 0.002 * total_area
    max_count_1 = max(1, int(0.002 * base_labels.size))
    selected_sorted_1 = sorted_candidate_1 & (cum_move_area_1 <= max_move_area_1) & (cum_count_1 <= max_count_1)
    selected_1 = selected_sorted_1[np.argsort(order_1)]
    labels_stage1 = np.where(selected_1, 1 - base_labels, base_labels)
    top_count_1 = np.sum(labels_stage1 == 1)
    bottom_count_1 = labels_stage1.size - top_count_1
    if top_count_1 == 0 or bottom_count_1 == 0:
        return base_labels

    top_mask_2 = labels_stage1 == 1
    bottom_mask_2 = labels_stage1 == 0
    top_area_2 = np.sum(areas_eff * top_mask_2)
    bottom_area_2 = np.sum(areas_eff * bottom_mask_2)
    top_center_2 = np.sum(embeddings * (areas_eff * top_mask_2)[:, None], axis=0) / np.maximum(top_area_2, 1e-12)
    bottom_center_2 = np.sum(embeddings * (areas_eff * bottom_mask_2)[:, None], axis=0) / np.maximum(bottom_area_2, 1e-12)
    d_top_2 = np.sum((embeddings - top_center_2) ** 2, axis=1)
    d_bottom_2 = np.sum((embeddings - bottom_center_2) ** 2, axis=1)
    margin_2 = d_bottom_2 - d_top_2
    violation_2 = np.where(labels_stage1 == 1, -margin_2, margin_2)
    top_share_2 = top_area_2 / np.maximum(total_area, 1e-12)
    move_top_to_bottom_2 = top_share_2 > balance_target
    candidate_2 = np.where(
        move_top_to_bottom_2,
        (labels_stage1 == 1) & (violation_2 > 0.0),
        (labels_stage1 == 0) & (violation_2 > 0.0),
    )
    priority_2 = np.where(candidate_2, violation_2 / areas_eff, -1.0)
    order_2 = np.argsort(-priority_2)
    sorted_candidate_2 = candidate_2[order_2]
    sorted_areas_2 = areas_eff[order_2]
    move_areas_2 = np.where(sorted_candidate_2, sorted_areas_2, 0.0)
    cum_move_area_2 = np.cumsum(move_areas_2)
    cum_count_2 = np.cumsum(sorted_candidate_2)
    max_move_area_2 = 0.001 * total_area
    max_count_2 = max(1, int(0.001 * labels_stage1.size))
    selected_sorted_2 = sorted_candidate_2 & (cum_move_area_2 <= max_move_area_2) & (cum_count_2 <= max_count_2)
    selected_2 = selected_sorted_2[np.argsort(order_2)]
    new_labels = np.where(selected_2, 1 - labels_stage1, labels_stage1)
    top_count_2 = np.sum(new_labels == 1)
    bottom_count_2 = new_labels.size - top_count_2
    if top_count_2 == 0 or bottom_count_2 == 0:
        return labels_stage1
    return new_labels
