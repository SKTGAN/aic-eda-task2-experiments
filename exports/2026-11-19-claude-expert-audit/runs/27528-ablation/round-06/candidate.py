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
    """Parent: pair-only random-walk logsigmoid objective.

    Change relative to the parent: retain the exact positive/negative
    logsigmoid pair objective, but add a timing-weighted margin-linear
    star-edge separation penalty on graph_scores.  The penalty is active when
    connected groups remain aligned on a timing-weighted net, with a small
    negative margin so even weakly aligned critical edges receive direct
    linear gradient.  This is intended to move the discrete two-means
    partition, not merely lower the training loss.

    Expected measurable effect: more cells should change assignment relative
    to the parent, and timing-weighted cut should fall on critical nets,
    improving WNS/TNS where the parent left labels unchanged.
    Invalidating result: partition diagnostics remain mostly unchanged, or
    timing worsens without additional label movement.
    """
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    active_star_penalty = F.relu(graph_scores + 0.1)
    weighted_star_cut = (graph_weights * active_star_penalty).sum()
    normalizer = graph_weights.sum().clamp(min=1.0)
    graph_penalty = weighted_star_cut / normalizer

    return pair_loss + 2.0 * graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Parent decoder unchanged: frozen area-balanced global two-way helper."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
