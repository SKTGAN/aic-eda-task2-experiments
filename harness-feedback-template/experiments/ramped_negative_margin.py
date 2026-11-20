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
    """Learn the initial grouping before strengthening hard-negative separation."""
    sampled_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    )
    hard_negative_loss = F.relu(negative_scores - 0.25).square().sum()
    # Epoch midpoints give a mean weight of 0.125 over the effective budget.
    margin_weight = 0.25 * (epoch + 0.5) / max(1, max_epochs)
    return (sampled_loss + margin_weight * hard_negative_loss) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Use the official area-balanced decoder to isolate the loss change."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
# EVOLVE-BLOCK-END
