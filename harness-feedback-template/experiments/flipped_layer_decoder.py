# EVOLVE-BLOCK-START
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
    """Keep the initial embedding objective to isolate layer orientation."""
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Evaluate the same grouping with the two die assignments exchanged."""
    labels = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    return 1 - labels
# EVOLVE-BLOCK-END
