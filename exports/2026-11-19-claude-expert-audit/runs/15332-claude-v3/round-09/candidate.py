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
    """Change vs parent: keep the parent's sampled log-sigmoid contrastive term,
    and add two geometric terms: (1) a net-weight-normalized softplus margin on
    timing-star edges to pull timing-critical connected supernodes together, and
    (2) a mean-centering term that maximizes global embedding variance. The
    star margin encourages graph communities to contract, while the centering
    term prevents collapse and pushes the embeddings toward a two-cluster
    antipodal geometry that the area-balanced two-means decoder can split.
    Expected measurable effect: more discrete partition changes and improved
    timing alignment on the full physical flow. Hypothesis invalidated if
    assignments remain mostly identical or if WNS/TNS regress without offset.
    """
    contrastive = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    graph_penalty = (
        graph_weights * F.softplus(0.5 - graph_scores)
    ).sum() / (graph_weights.sum() + 1e-8)

    mu = torch.mean(embeddings, dim=0)
    centering = torch.sum(torch.square(mu))

    return contrastive + 2.0 * graph_penalty + 1.0 * centering


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder (unchanged)."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
