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
    """Mechanism: keep the frozen random-walk logistic objective and add an
    area-weighted dispersion reward, i.e. minimize the squared norm of the
    physical-area-weighted mean embedding (which equals maximizing the
    area-weighted variance of L2-normalized embeddings), ramped in over the
    epoch budget; Decision: the penalty changes how strongly each supernode
    embedding is pulled toward the global area-weighted centroid, which moves
    the two area-weighted centers that the unchanged decoder forms and hence
    the tier given to supernodes near the two-means boundary; Prediction: the
    embedding cloud becomes more antipodal and less seed-dependent, so the
    bp-ng45 mean paired score rises on most of its seeds versus this parent;
    Falsifier: bp-ng45 mean paired score does not exceed the parent, or any
    training case mean falls by more than its 5.0 tolerance."""
    walk_term = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    total_area = node_areas.sum()
    area_share = node_areas / torch.clamp(total_area, min=1e-6)
    centroid = (embeddings * area_share[:, None]).sum(dim=0)
    centroid_energy = (centroid * centroid).sum()
    safe_energy = torch.where(
        torch.isfinite(centroid_energy),
        centroid_energy,
        torch.zeros_like(centroid_energy),
    )
    progress = (float(epoch) + 1.0) / float(max(1, int(max_epochs)))
    strength = 0.5 * min(1.0, progress)
    return walk_term + strength * safe_energy


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Reproduce the frozen area-balanced global two-way decoder."""
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
