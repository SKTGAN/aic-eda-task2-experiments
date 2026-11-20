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
    """Replace the parent's linearly weighted star-edge soft cut with a log-bounded version.

    Relative to the parent, the positive/negative pair objective is unchanged.
    The timing-star penalty changes from
    `sum(w * sigmoid(score)) / sum(w)` to
    `sum(log1p(w * sigmoid(score))) / sum(log1p(w))`, preserving the same
    per-edge direction but compressing high-weight domination. The expected
    measurable effect is recovery on the regressed ariane133/1003 seed while
    retaining the ariane133/1002 gain through the unchanged frozen two-means
    decoder and protected feasibility closure. The hypothesis is invalidated
    if the target gain is below 2.0, protected loss exceeds 2.0, or labels stay
    unchanged while timing changes.
    """
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_edge_signal = graph_weights * torch.sigmoid(graph_scores)
    graph_edge_term = torch.log1p(graph_edge_signal)
    graph_weight_term = torch.log1p(graph_weights)

    graph_denom = torch.clamp(graph_weight_term.sum(), min=1e-6)
    graph_penalty = graph_edge_term.sum() / graph_denom

    return pair_loss + 0.10 * graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the parent decoder: frozen area-balanced global two-way clustering."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
