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
    """Use excess timing weight to pull together the ends of important nets."""
    sampled = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    # The published star weights already divide each net's weight among its edges.
    edge_net_weight = net_weights[graph_net_ids]
    criticality = graph_weights * (edge_net_weight - 1.0) / edge_net_weight
    pull = (criticality * (1.0 - graph_scores)).sum()
    pull = pull / torch.clamp(criticality.sum(), min=1e-12)
    return sampled + pull


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
# EVOLVE-BLOCK-END
