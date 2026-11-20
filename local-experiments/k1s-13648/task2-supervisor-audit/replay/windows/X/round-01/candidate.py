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
    """Parent loss plus a normalized timing-weighted star-edge attraction term.

    Change versus parent: keep the random-walk positive/negative objective and
    add a smooth, timing-weight-normalized penalty on low star-edge similarity.
    This encourages net-connected supernodes, especially high-timing-weight
    nets, to land closer in embedding space before the unchanged decoder forms
    two area-balanced groups. Expected measurable effect: lower timing-weighted
    cut and TNS improvement, with WNS a possible trade-off. The hypothesis is
    invalidated if matched case/seed evaluations show no combined gain, or if
    decoder labels remain mostly unchanged while timing differs only physically.
    """
    pair_term = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    edge_weight_sum = graph_weights.sum()
    safe_edge_weight_sum = torch.clamp(edge_weight_sum, min=1e-12)

    timing_edge_penalty = (
        F.softplus(-graph_scores) * graph_weights
    ).sum() / safe_edge_weight_sum

    return pair_term + 0.5 * timing_edge_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the parent decoder unchanged: frozen area-balanced global two-way.

    Change versus parent: none. This preserves the seeded, area-weighted
    two-means handoff so the loss-only edit can be assessed against the same
    protected feasibility closure and discrete assignment mechanism.
    """
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
