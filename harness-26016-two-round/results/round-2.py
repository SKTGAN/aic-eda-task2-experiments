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
    """Mechanism: the parent loss averages summed positive and negative log-sigmoid terms by source_batch_size; the edit keeps that normalization but adds a mean-centered timing-criticality reweighting of the existing positive random-walk pairs, without adding a full graph-edge term; Decision: each positive pair is reweighted by the mean standardized slack criticality of its endpoints, so critical observed pairs receive stronger attraction while noncritical observed pairs receive weaker attraction; Prediction: critical connected groups should obtain higher cosine similarity, lowering timing-weighted cut on affected seeds and improving TNS without the broad repair movement caused by full star-edge attraction; Falsifier: if matched cells show no lower timing-weighted cut or TNS does not improve or regresses, the critical-pair reweighting hypothesis is disproved."""
    positive_sum = F.logsigmoid(positive_scores).sum()
    negative_sum = F.logsigmoid(-negative_scores).sum()
    base_loss = -(positive_sum + negative_sum) / max(1, source_batch_size)

    coverage_raw = node_features[:, 6]
    coverage = torch.where(
        torch.isfinite(coverage_raw),
        torch.clamp(coverage_raw, 0.0, 1.0),
        torch.zeros_like(coverage_raw),
    )

    slack_raw = 0.5 * (node_features[:, 0] + node_features[:, 1])
    slack = torch.where(
        torch.isfinite(slack_raw),
        slack_raw,
        torch.zeros_like(slack_raw),
    )

    valid_mass = coverage.sum()
    valid_denom = torch.clamp(valid_mass, min=1.0)
    slack_mean = (slack * coverage).sum() / valid_denom
    centered_slack = slack - slack_mean
    slack_scale = torch.sqrt(
        (centered_slack * centered_slack * coverage).sum() / valid_denom
    )
    slack_scale = torch.clamp(slack_scale, min=1e-3)
    criticality = torch.sigmoid(-centered_slack / slack_scale) * coverage

    pair_criticality = 0.5 * (
        criticality[positive_sources] + criticality[positive_targets]
    )
    pair_mean = pair_criticality.sum() / max(1, len(pair_criticality))
    pair_delta = 0.5 * (pair_criticality - pair_mean)

    timing_delta = -(
        F.logsigmoid(positive_scores) * pair_delta
    ).sum() / max(1, source_batch_size)

    return base_loss + 0.5 * timing_delta


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
