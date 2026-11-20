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
    """Parent random-walk contrastive loss plus a timing-criticality alignment term.

    Relative to the parent, this keeps the random-walk positive/negative objective
    and adds a weighted regression of the first embedding coordinate onto a bounded
    per-node criticality target derived from worst slack (node_features[:, 0]) with
    timing coverage (node_features[:, 6]) as confidence. Expected measurable effect:
    the area-weighted two-means decoder receives a timing-relevant embedding axis
    that moves groups across the area-balanced boundary, changing the discrete
    partition and improving WNS/TNS. The hypothesis is invalidated if final labels
    remain identical up to a die swap or if timing does not improve versus parent.
    """
    base = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    coverage = torch.clamp(node_features[:, 6], 0.0, 1.0)
    known = coverage
    denom = torch.clamp(known.sum(), min=1.0)

    criticality = -node_features[:, 0] * known
    mean_c = (criticality * known).sum() / denom
    var_c = (torch.square(criticality - mean_c) * known).sum() / denom
    scale_c = torch.sqrt(torch.clamp(var_c, min=0.0) + 1e-6)

    target = torch.tanh((criticality - mean_c) / (scale_c + 1e-6))
    target = target * known

    align = (known * torch.square(embeddings[:, 0] - target)).sum() / denom
    return base + align


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder unchanged."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
