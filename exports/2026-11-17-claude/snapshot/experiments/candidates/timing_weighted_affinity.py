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
    """Encourage embedding agreement on nets with higher timing weight."""
    sampled_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    # Each net's weight is already divided among its star edges.
    affinity_loss = (graph_weights * (1.0 - graph_scores)).sum()
    affinity_loss = affinity_loss / graph_weights.sum().clamp_min(1e-12)
    return sampled_loss + 4.0 * affinity_loss


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the official decoder so the experiment isolates the loss change."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
# EVOLVE-BLOCK-END
