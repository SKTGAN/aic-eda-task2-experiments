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
    """Refine parent criticality reweighting with negative-pair criticality gating.

    Change versus the parent: keep the exact positive-pair worst-slack reweighting,
    but add a coverage-masked criticality weight on sampled negative pairs. When
    both negative endpoints have poor known slack, their separation term is
    downweighted; unknown-timing endpoints are neutral so zero coverage is not
    treated as noncritical evidence. This targets the parent's ariane133 seed1001
    WNS regression by avoiding forced separation of timing-critical groups that
    were not captured by a positive random-walk pair.

    Expected measurable effect: the unchanged seeded area-balanced two-means
    decoder should move at least one critical group across the area-balanced
    boundary, reducing the WNS regression while retaining the parent TNS gain.

    Hypothesis-invalidating result: unchanged assignments on most cells, no
    reduction in the ariane133 seed1001 WNS deficit, or broad regression from
    weakened negative separation would invalidate the negative-gating mechanism.
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

    negative_criticality_z = torch.where(
        known_timing,
        criticality_z,
        torch.zeros_like(criticality_z),
    )
    negative_criticality = 0.5 * (
        negative_criticality_z[negative_sources]
        + negative_criticality_z[negative_targets]
    )
    negative_weight = 1.0 - 0.28 * (torch.sigmoid(negative_criticality) - 0.5)

    positive_loss = -(
        positive_weight * F.logsigmoid(positive_scores)
    ).sum() / max(1, source_batch_size)
    negative_loss = -(
        negative_weight * F.logsigmoid(-negative_scores)
    ).sum() / max(1, source_batch_size)
    return positive_loss + negative_loss


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder.

    Change versus the parent: none. The decoder call and behavior are unchanged so
    this candidate isolates the loss-side negative-pair criticality gating.
    Expected measurable effect: any timing change is attributable to the loss and
    must still pass through the same seeded two-means and protected feasibility
    closure. Hypothesis-invalidating result: identical final assignments with no
    timing change would confirm this decoder handoff was not reached.
    """
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
