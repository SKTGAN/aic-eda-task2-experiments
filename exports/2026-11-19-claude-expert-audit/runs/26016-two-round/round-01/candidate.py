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
    """Mechanism: add a normalized timing-weighted star-edge attraction (1 - graph_scores) to the unchanged random-walk logsigmoid pair loss; Decision: each connected net star contributes graph_weights-normalized attraction, changing embeddings but not the decoder; Prediction: critical connected supernodes should co-locate, lowering timing-weighted cut and improving TNS after feasible partitioning; Falsifier: if matched cells show no lower timing-weighted cut or TNS worsens, the graph-attraction hypothesis is disproved."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_weight_sum = graph_weights.sum()
    graph_penalty = torch.where(
        graph_weight_sum > 0,
        (graph_weights * (1.0 - graph_scores)).sum()
        / torch.clamp(graph_weight_sum, min=1e-6),
        torch.zeros_like(graph_weight_sum),
    )
    return pair_loss + 0.2 * graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
