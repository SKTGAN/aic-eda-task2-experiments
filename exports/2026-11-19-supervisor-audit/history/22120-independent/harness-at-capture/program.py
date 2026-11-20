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
    """Parent criticality reweighting plus a criticality Fisher-separation term.

    Change versus the parent: keep the parent's positive-pair worst-slack
    reweighting and its negative logistic objective, but add a different
    embedding-geometry mechanism.  Coverage-masked standardized criticality is
    used as a soft pseudo-label; the new term maximizes the squared norm of the
    criticality-weighted mean embedding direction.  This directly increases the
    between-class separation that the frozen two-means decoder can see, rather
    than only reweighting individual positive pairs.  The decoder is unchanged.

    Expected measurable effect: embeddings acquire a timing-correlated
    direction, so the area-balanced two-way split moves across the embedding
    boundary and reduces critical-net cuts, improving WNS/TNS on critical
    designs without discarding the parent random-walk geometry.

    Hypothesis-invalidating result: if final assignments remain mostly
    unchanged versus the parent, or if timing regresses broadly while the
    criticality direction is present, then this added geometry is not reaching
    the discrete partition in a useful way.
    """
    slack_values = node_features[:, 0]
    coverage_values = node_features[:, 6]
    known_timing = coverage_values > 0
    criticality = torch.where(
        known_timing,
        F.relu(-slack_values),
        torch.zeros_like(slack_values),
    )
    criticality_mean = torch.mean(criticality)
    criticality_scale = torch.sqrt(
        torch.mean(torch.square(criticality - criticality_mean)) + 1e-6
    )
    criticality_z = (criticality - criticality_mean) / criticality_scale
    positive_criticality = 0.5 * (
        criticality_z[positive_sources] + criticality_z[positive_targets]
    )
    positive_weight = 1.0 + 0.30 * (torch.sigmoid(positive_criticality) - 0.5)
    positive_loss = -(
        positive_weight * F.logsigmoid(positive_scores)
    ).sum() / max(1, source_batch_size)
    negative_loss = -F.logsigmoid(-negative_scores).sum() / max(1, source_batch_size)

    criticality_target = torch.where(
        known_timing,
        torch.tanh(1.75 * criticality_z),
        torch.zeros_like(criticality_z),
    )
    criticality_direction = torch.mean(
        criticality_target[:, None] * embeddings,
        dim=0,
    )
    separation_loss = -0.30 * float(embeddings.shape[1]) * torch.sum(
        torch.square(criticality_direction)
    )

    return positive_loss + negative_loss + separation_loss


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder.

    Change versus the parent: none.  The decoder call and behavior are unchanged
    so this candidate isolates the loss-side criticality Fisher-separation
    mechanism.  Expected measurable effect: any timing change must pass through
    the same seeded two-means and protected feasibility closure.

    Hypothesis-invalidating result: identical final assignments with no timing
    change would show that the loss geometry did not move the decoder boundary.
    """
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
