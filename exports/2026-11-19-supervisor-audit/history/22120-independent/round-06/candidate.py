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
    """Add timing-weighted star-edge smoothness to the parent contrastive loss.

    Change relative to parent: keep the maintained random-walk positive/negative
    objective, and add a normalized penalty ``softplus(-graph_dot)`` on supplied
    star edges weighted by their fixed timing weights. This encourages groups
    connected by timing-critical nets to remain similar in embedding space,
    so the unchanged area-balanced decoder can keep those groups together.

    Expected measurable effect: lower timing-weighted graph cut proxy during
    training and altered final die labels, with possible TNS improvement.
    Invalidating result: labels remain unchanged up to die swap, or the
    official timing score regresses without reducing the graph cut proxy.
    """
    contrastive = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_denom = graph_weights.sum().clamp(min=1.0)
    graph_smoothness = (
        graph_weights * F.softplus(-graph_scores)
    ).sum() / graph_denom

    return contrastive + 1.5 * graph_smoothness


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the parent decoder: frozen area-balanced global two-way clustering."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
