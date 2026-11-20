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
    """Parent random-walk contrastive loss plus criticality geometry alignment.

    Change versus parent: keep the maintained positive/negative objective and
    add a masked, standardized worst-slack alignment penalty on the embedding
    direction that the unchanged area-balanced two-means can split. The target
    is derived from node_features' worst-slack column, using coverage to avoid
    treating unknown timing as critical. Expected measurable effect: the fixed
    two-way decoder should place timing-critical groups on one side more often,
    changing discrete die labels and improving TNS/WNS without decoder edits.
    Falsifier: the decoder keeps the start grouping on most cells, or bp-ng45
    TNS regresses with the new labels.
    """
    base = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    coverage = node_features[:, 6]
    valid = torch.where(
        coverage > 0.0,
        torch.ones_like(coverage),
        torch.zeros_like(coverage),
    )
    valid_count = torch.clamp(valid.sum(), min=1.0)

    slack = node_features[:, 0]
    slack_mean = (slack * valid).sum() / valid_count
    slack_centered = (slack - slack_mean) * valid
    slack_var = (slack_centered * slack_centered).sum() / valid_count
    slack_std = torch.sqrt(torch.clamp(slack_var, min=1.0e-6))
    criticality = -slack_centered / slack_std

    embedding_dim = float(embeddings.shape[1])
    unit_scale = torch.sqrt(
        torch.clamp(
            torch.ones_like(embeddings[:, 0]) * embedding_dim,
            min=1.0,
        )
    )
    projection = embeddings.sum(dim=1) / unit_scale

    alignment = (
        torch.square(projection - criticality) * valid
    ).sum() / valid_count

    return base + 1.0 * alignment


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Unchanged parent decoder: frozen area-balanced global two-way split."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
