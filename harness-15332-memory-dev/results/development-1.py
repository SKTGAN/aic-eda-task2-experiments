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
    """Stabilize the parent round-4 timing-star attraction with a warmup ramp.

    Change relative to the parent: the sampled random-walk log-sigmoid
    contrastive term and the graph_weights-normalized softplus margin on
    timing star edges are kept unchanged, but the graph term coefficient is
    multiplied by a linear ramp over the first 10% of the effective epoch
    budget.  The loss interface exposes no gradient-norm or detach primitive,
    so this uses the legal warmup ramp as the per-step stabilizer instead of
    an exact gradient-norm cap; the existing graph-weight normalization still
    limits early graph dominance.

    Expected measurable effect: the round-4 timing-star attraction remains
    active after warmup, but early batches cannot let the graph margin
    overwhelm the contrastive objective.  The unchanged area-balanced
    two-center decoder should preserve the ariane133-ng45 partition gains
    while reducing sensitivity to early graph-margin dominance.

    Invalidation: in same-host paired reruns, reject if the mean score delta
    versus round 4 is <= 0, or if ariane133-ng45/1002 fails to match round 4
    while labels_changed rises.
    """
    contrastive_loss = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_margin_penalty = (
        graph_weights * F.softplus(0.5 - graph_scores)
    ).sum() / graph_weights.sum().clamp(min=1.0)

    warmup_epochs = max(1.0, 0.1 * float(max_epochs))
    ramp = min(1.0, float(epoch) / warmup_epochs)
    graph_scale = 4.0 * ramp

    return contrastive_loss + graph_scale * graph_margin_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the parent frozen area-balanced global two-way decoder.

    No change relative to the parent: this still delegates exactly once to the
    trusted reference helper with unchanged arguments.  The hypothesis is
    isolated to loss stabilization, so the decoder's measurable behavior
    should remain unchanged.  If decoder-side behavior changes, the comparison
    does not test the intended loss-only hypothesis.
    """
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
