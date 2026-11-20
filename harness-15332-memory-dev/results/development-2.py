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
    """Keep the parent timing-star attraction but saturate each net's contribution.

    Change relative to the parent: the sampled random-walk log-sigmoid
    contrastive objective is unchanged, and the timing-weighted star-edge
    margin attraction is retained.  Each edge penalty is passed through a
    smooth saturating map ``cap * tanh(softplus(0.5 - score) / cap)`` before
    weighting.  Because ``graph_weights`` sum to each represented net's fixed
    timing weight, this bounds every net's total graph contribution by
    ``net_weight * cap`` while keeping non-zero gradients.  The intent is to
    preserve the parent's timing-driven partition movement but stop a few
    high-loss critical nets from dominating the embedding geometry.

    Expected measurable effect: the unchanged area-balanced two-center decoder
    should still move boundary supernodes, retaining the parent's ariane gains
    while reducing the bp/bp_fe regressions caused by aggressive critical-net
    attraction.

    Invalidation: if the official nine-cell mean score does not exceed the
    parent round-4 mean, or if label changes and timing gains disappear, the
    saturating per-net contribution cap is not useful.
    """
    contrastive_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    cap = 1.5
    edge_penalty = F.softplus(0.5 - graph_scores)
    capped_penalty = cap * torch.tanh(edge_penalty / cap)
    graph_penalty = (
        graph_weights * capped_penalty
    ).sum() / graph_weights.sum().clamp(min=1.0)

    return contrastive_loss + 4.0 * graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the parent frozen area-balanced global two-way decoder.

    No change relative to the parent: this still delegates exactly once to the
    trusted reference helper with unchanged arguments.  The hypothesis is
    isolated to the loss geometry, so the decoder's measurable behavior should
    remain unchanged.  If decoder-side behavior changes, the comparison does
    not test the intended loss-only hypothesis.
    """
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
