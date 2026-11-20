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
    """Parent: maintained random-walk pair objective only. This version keeps
    the positive/negative logsigmoid pair terms unchanged and adds a
    timing-weighted star-edge soft-cut penalty normalized by the active graph
    weight sum, encouraging represented-net endpoints to have higher cosine
    similarity. Expected measurable effect: timing-critical connected groups
    move together in embedding space, so the unchanged area-balanced two-means
    decoder can place them on one die and alter some discrete labels. Result
    that would invalidate the hypothesis: no feasible-label change, or no
    positive paired WNS/TNS effect versus the parent.
    """
    pair_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_weight_total = torch.clamp(graph_weights.sum(), min=1e-6)
    graph_score_clamped = torch.clamp(graph_scores, min=-1.0, max=1.0)
    graph_cut_energy = (
        graph_weights * (1.0 - graph_score_clamped)
    ).sum()
    graph_cut_penalty = graph_cut_energy / graph_weight_total

    return pair_loss + 0.5 * graph_cut_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Unchanged from the parent: reproduce the frozen area-balanced global
    two-way decoder through the official reference helper."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
