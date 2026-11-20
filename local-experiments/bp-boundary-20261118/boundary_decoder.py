# EVOLVE-BLOCK-START
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
    """Reproduce the maintained random-walk negative-sampling objective."""
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Rerank the ambiguous groups by a variance-shrunk center margin within the original local area budget."""
    initial = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    top_count = int(np.sum(initial))
    width = min(max(1, len(initial) // 20), top_count - 1, len(initial) - top_count - 1)
    if width < 1:
        return initial
    top_weights = node_areas * initial
    bottom_weights = node_areas * (1 - initial)
    top_center = np.sum(embeddings * top_weights[:, None], axis=0) / max(np.sum(top_weights), 1e-12)
    bottom_center = np.sum(embeddings * bottom_weights[:, None], axis=0) / max(np.sum(bottom_weights), 1e-12)
    direction = top_center - bottom_center
    preference = np.sum(embeddings * direction, axis=1)
    top_edge = np.argsort(np.lexsort((preference, 1 - initial))) < width
    bottom_edge = np.argsort(np.lexsort((-preference, initial))) < width
    band = np.maximum(top_edge, bottom_edge)
    local_points = embeddings[band]
    local_center = np.mean(local_points, axis=0)
    local_variance = np.mean(np.square(local_points - local_center), axis=0)
    ridge = np.mean(local_variance) + 1e-12
    tilted_direction = direction / np.sqrt(1.0 + local_variance / ridge)
    tilted_margin = np.sum(embeddings * tilted_direction, axis=1)
    reranked = np.lexsort((-tilted_margin, 1 - band.astype(np.int64)))
    local_target = np.sum(node_areas[top_edge])
    area_prefix = np.cumsum(node_areas[reranked[:2 * width]])[:-1]
    cut = int(np.argmin(np.abs(area_prefix - local_target)))
    if abs(area_prefix[cut] - local_target) > 0.002 * np.sum(node_areas):
        return initial
    restored = np.argsort(reranked) <= cut
    return np.where(band, restored, initial).astype(np.int64)
# EVOLVE-BLOCK-END
