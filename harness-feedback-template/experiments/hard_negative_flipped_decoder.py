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
    """Keep the fixed additional penalty for strongly similar negative pairs."""
    sampled_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    )
    hard_negative_loss = F.relu(negative_scores - 0.25).square().sum()
    return (sampled_loss + 0.25 * hard_negative_loss) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Exchange the layers after clustering the margin-trained embeddings."""
    labels = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    return 1 - labels
# EVOLVE-BLOCK-END
