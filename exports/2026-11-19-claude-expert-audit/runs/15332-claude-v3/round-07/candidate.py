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
    """Add a stronger timing-weighted star-edge attraction term to the parent loss.

    Change relative to the parent: keep the sampled random-walk log-sigmoid
    contrastive objective unchanged, and add a normalized timing-weighted
    margin attraction on the supplied timing-context star edges.  The margin
    term pushes endpoints of timing-weighted connected nets toward a positive
    embedding dot product, with normalization by total graph edge weight so the
    graph term remains comparable across nets.

    Expected measurable effect: the timing-weighted graph attraction reshapes
    embeddings more strongly, so the unchanged area-balanced two-center decoder
    should move at least a few supernodes across the partition boundary and
    improve TNS where timing-weighted connectivity is informative.  The main
    risk is a WNS regression on bp_fe-ng45.

    Invalidation: if the official labels remain unchanged on most training
    cells, or if the combined score does not exceed the parent, this stronger
    graph-attraction mechanism is not useful.
    """
    contrastive_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_margin_penalty = (
        graph_weights * F.softplus(0.5 - graph_scores)
    ).sum() / graph_weights.sum().clamp(min=1.0)

    return contrastive_loss + 4.0 * graph_margin_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Refine the parent reference partition with one area-aware Lloyd correction.

    Change relative to the parent: still call the trusted reference helper
    exactly once with unchanged inputs to obtain a legal, area-balanced start.
    Then perform exactly one non-iterative reassignment: rebuild the two
    physical-area-weighted centers from the helper labels and move only
    boundary nodes from the currently larger-area side to the other side when
    they are geometrically closer to that other center.  No random state, no
    loop, and no full label swap are introduced.

    Expected measurable effect: a small number of boundary supernodes that the
    reference area rounding left on the larger side but whose embeddings place
    them nearer the opposite center will cross the boundary, improving final
    TNS without the broad die-swap regression seen from full custom re-clustering.

    Invalidation: if labels remain identical on most cells, or if the combined
    score does not exceed the parent, or if a die swap appears, this refinement
    is not useful.
    """
    base_labels = reference_global_two_way(
        embeddings, node_areas, seed, max_iterations, balance_target
    )

    top_mask = base_labels == 1
    bottom_mask = base_labels == 0

    top_area = (node_areas * top_mask).sum()
    bottom_area = (node_areas * bottom_mask).sum()

    top_center = (
        embeddings * (node_areas * top_mask)[:, None]
    ).sum(axis=0) / (top_area + 1e-12)
    bottom_center = (
        embeddings * (node_areas * bottom_mask)[:, None]
    ).sum(axis=0) / (bottom_area + 1e-12)

    top_distance = ((embeddings - top_center) ** 2).sum(axis=1)
    bottom_distance = ((embeddings - bottom_center) ** 2).sum(axis=1)

    if top_area >= bottom_area:
        move_mask = top_mask & (bottom_distance < top_distance)
    else:
        move_mask = bottom_mask & (top_distance < bottom_distance)

    refined_labels = np.where(move_mask, 1 - base_labels, base_labels)

    top_count = refined_labels.sum()
    total_count = refined_labels.size
    if top_count == 0 or top_count == total_count:
        return base_labels

    return refined_labels
