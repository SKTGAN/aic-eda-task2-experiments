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
    """Parent keeps only the random-walk pair objective. This version keeps that
    positive/negative logsigmoid term and adds a timing-weighted graph attraction
    term: strongly connected star edges are pulled toward positive embedding dot
    products. Expected effect: the frozen area-balanced two-means decoder sees a
    timing-aware embedding geometry and changes its discrete die split, improving
    timing-weighted cut/TNS on some cases. Invalidated if the partition diagnostic
    is mostly unchanged or if paired score regresses broadly without a cut shift.
    """
    pair_term = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_weight_total = graph_weights.sum()
    graph_attraction = -(
        graph_weights * graph_scores
    ).sum() / torch.clamp(graph_weight_total, min=1e-6)

    return pair_term + 0.5 * graph_attraction


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Unchanged from the parent: reproduce the frozen area-balanced global
    two-way decoder so only the loss geometry changes in this candidate."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
