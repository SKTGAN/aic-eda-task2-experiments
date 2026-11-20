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
    """Negative sampling plus timing-weighted star-edge attraction.

    Change: retain the maintained random-walk negative-sampling objective, but
    add a normalized regularizer that raises cosine similarity along supplied
    timing-weighted star edges via graph_scores and graph_weights. Expected
    measurable effect: lower timing-weighted cut and improved TNS/WNS after the
    unchanged area-balanced decoder. The ramp starts weak and reaches full
    strength late in training. Observation against: if timing score does not
    improve while the graph term falls, or if negative-sampling loss rises
    sharply from excessive embedding collapse, the mechanism is not helping.
    """
    sampled_term = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    graph_weight_total = torch.sum(graph_weights)
    graph_penalty = torch.sum(
        graph_weights * F.softplus(-graph_scores)
    ) / (graph_weight_total + 1e-6)
    progress = min(1.0, epoch / max_epochs)
    graph_scale = 0.5 * (0.25 + 0.75 * progress)
    return sampled_term + graph_scale * graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
