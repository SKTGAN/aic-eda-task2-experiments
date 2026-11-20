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
    """Mechanism: add a timing-weight-normalized star-edge attraction term to the maintained pair objective; Decision: raise the loss when high-weight graph-connected supernode embeddings are dissimilar, pushing them toward the same unchanged decoder tier; Prediction: the target case's mean paired score rises with a less-negative TNS deficit while other case means stay within tolerance; Falsifier: target-case mean paired score delta is non-positive, or any case mean falls more than 5 points below the parent."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    graph_weight_total = graph_weights.sum() + 1e-6
    graph_attraction = (
        F.softplus(-graph_scores) * graph_weights
    ).sum() / graph_weight_total
    return pair_loss + 0.35 * graph_attraction


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
