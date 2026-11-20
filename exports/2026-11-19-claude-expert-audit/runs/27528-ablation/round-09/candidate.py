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
    """Parent: maintained random-walk pair logsigmoid objective only.

    Change relative to the parent: retain that exact positive/negative
    logsigmoid pair term and add a timing-weighted, weight-normalized
    softplus star-edge SEPARATION penalty on the supplied ``graph_scores``.
    Minimizing ``softplus(dot - margin)`` drives connected supernodes of a
    represented net toward lower (more negative) star dot products, i.e. it
    pushes the endpoints of heavily weighted (critical) nets apart.  Unlike a
    ReLU form that activates only above the margin, the softplus form carries a
    nonzero gradient on every star edge, so many more groups feel the pull and
    the area-weighted round-to-centroid step can move them across the
    area-balanced boundary.

    Expected measurable effect: the discrete two-means partition separates on
    more cells than the prior graph-attraction attempt (which kept the start
    grouping and scored -11.23); the timing-weighted cut should improve on at
    least the ariane133 cells while staying legal after native closure.

    Falsifier: if ariane133/1001 and bp_fe cells keep the start labels with no
    timing gain, or bp-ng45/1002 regresses further without any label movement,
    the dense-gradient separation hypothesis is wrong.
    """
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    margin = 0.5
    sep_edges = F.softplus(graph_scores - margin)
    weight_mass = graph_weights.sum()
    star_sep = (graph_weights * sep_edges).sum() / (weight_mass + 1e-6)
    return pair_loss + 0.1 * star_sep


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Unchanged from the parent: frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
