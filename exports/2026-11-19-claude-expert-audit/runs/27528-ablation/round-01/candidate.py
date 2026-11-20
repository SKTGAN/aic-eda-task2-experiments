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
    """Add a small timing-weighted star-edge soft cut penalty to the parent.

    Relative to the parent random-walk objective, this keeps the positive and
    negative pair terms unchanged and adds
    `0.10 * sum(graph_weights * sigmoid(graph_scores)) / sum(graph_weights)`.
    The intended effect is to pull timing-critical connected supernodes toward
    the same embedding region, which can move the existing area-balanced
    two-means boundary and improve TNS while leaving WNS neutral or improved.
    The hypothesis is invalidated if the official partition is mostly unchanged
    or if paired WNS/TNS do not improve after physical closure.
    """
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_denom = torch.clamp(graph_weights.sum(), min=1e-6)
    graph_penalty = (
        graph_weights * torch.sigmoid(graph_scores)
    ).sum() / graph_denom

    return pair_loss + 0.10 * graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the parent decoder: frozen area-balanced global two-way clustering."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
