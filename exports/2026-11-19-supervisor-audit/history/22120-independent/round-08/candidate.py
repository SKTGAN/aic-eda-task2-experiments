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
    """Parent random-walk contrastive loss with coverage-masked criticality reweighting.

    Change versus the parent: keep the same positive/negative logistic objective,
    but reweight each positive pair by the standardized worst-slack criticality of
    its endpoints. Unknown-timing nodes, marked by zero coverage, receive no
    criticality weight. This differs from a global criticality-alignment penalty:
    it preserves the learned random-walk communities and only shifts emphasis
    toward timing-critical positive pairs.

    Expected measurable effect: the frozen area-balanced two-means decoder should
    see embeddings shaped more strongly around critical connected groups, changing
    the discrete partition enough to improve timing-weighted cut and TNS without
    discarding the parent contrastive geometry.

    Hypothesis-invalidating result: no TNS improvement on critical ariane133 seeds,
    or a broad regression with mostly unchanged assignments versus the parent,
    would show that pair reweighting is not reaching the decoder boundary.
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
    return positive_loss + negative_loss


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder.

    Change versus the parent: none. The decoder call and behavior are unchanged so
    this candidate isolates the loss-side criticality reweighting mechanism.
    Expected measurable effect: any timing change is attributable to the loss and
    must still pass through the same seeded two-means and protected feasibility
    closure. Hypothesis-invalidating result: identical final assignments with no
    timing change would confirm this decoder handoff was not reached.
    """
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
