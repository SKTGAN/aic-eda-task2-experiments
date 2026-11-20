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
    """Mechanism: add a timing-weighted star-edge attraction term to the random-walk logistic loss; Decision: emphasize high-weight graph edges so critical connected groups become more similar and tend to share a die; Prediction: timing-critical cross-die cuts decrease and bp-ng45 mean paired timing score rises on most seeds; Falsifier: bp-ng45 mean paired score does not exceed the parent or a non-target case mean falls by more than its tolerance."""
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    edge_weight = graph_weights / (graph_weights.sum() + 1e-6)
    graph_attraction = (edge_weight * F.softplus(-graph_scores)).sum()
    return pair_loss + 0.20 * graph_attraction


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
