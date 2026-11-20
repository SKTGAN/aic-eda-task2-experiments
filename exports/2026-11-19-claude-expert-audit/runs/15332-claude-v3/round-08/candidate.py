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
    """Add a moderately scaled timing-weighted star attraction to the parent loss.

    Relative to the parent pure random-walk log-sigmoid objective, this keeps
    the sampled positive/negative contrastive term unchanged and adds a
    graph_weights-normalized softplus(-graph_scores) attraction over timing
    star edges. Connected supernodes on high-weight timing nets should move
    closer in embedding space, while sampled negative pairs remain separated.

    Expected measurable effect: timing-sensitive groups should more often cross
    the reference decoder's area-balanced boundary than in the parent, improving
    the physical WNS/TNS trade-off without the large bp_fe regression seen with
    a stronger unnormalized star term. This hypothesis is invalidated if most
    cells keep the start assignment with no timing gain, or if timing worsens
    broadly despite the normalized attraction.
    """
    contrastive_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    star_weight_sum = torch.clamp(graph_weights.sum(), min=1.0)
    star_attraction = (
        graph_weights * F.softplus(-graph_scores)
    ).sum() / star_weight_sum

    return contrastive_loss + 0.75 * star_attraction


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Unchanged from the parent: use the frozen area-balanced reference decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
