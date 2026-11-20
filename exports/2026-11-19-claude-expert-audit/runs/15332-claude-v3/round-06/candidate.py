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
    """Add a graph_weights-normalized timing-star attraction to the parent loss.

    Change relative to the parent: keep the parent sampled random-walk
    log-sigmoid contrastive objective unchanged, and add the weighted mean
    softplus(-graph_scores) over timing-context star edges. This uses the
    supplied graph weights as a normalized attraction, rather than an
    unnormalized edge-count sum, to pull embeddings of timing-critical
    connected supernodes together while limiting dense-net bias.
    Expected measurable effect: retain the timing gains seen from stronger
    star-edge attraction while reducing the bp_fe-ng45 regression, with the
    reference decoder and native feasibility closure unchanged.
    Invalidated if bp_fe-ng45/1001 does not improve, if the ariane133-ng45/1002
    TNS gain disappears, or if labels remain unchanged while timing moves.
    """
    contrastive_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    graph_weight_total = graph_weights.sum()
    graph_penalty = (
        graph_weights * F.softplus(-graph_scores)
    ).sum() / torch.clamp(graph_weight_total, min=1e-6)
    return contrastive_loss + 2.0 * graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the parent decoder behavior exactly unchanged.

    Change relative to the parent: none in the decoder. This isolates the loss
    hypothesis while preserving the frozen seeded area-balanced two-way
    handoff and native feasibility closure.
    Expected measurable effect: no decoder-side change; any timing difference
    must come from the edited embedding objective.
    Invalidated if decoder labels differ from the unchanged reference handoff
    for the same embeddings, seed, areas and limits.
    """
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
