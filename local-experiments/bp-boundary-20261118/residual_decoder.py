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
    """Split both reference strata along a residual embedding direction to retain a cross-axis centroid contrast after closure."""
    initial = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    top_count = int(np.sum(initial))
    bottom_count = len(initial) - top_count
    if min(top_count, bottom_count) < 2:
        return initial
    total = np.sum(node_areas)
    top_area = node_areas * initial
    bottom_area = node_areas * (1 - initial)
    first_center = np.sum(embeddings * top_area[:, None], axis=0) / max(np.sum(top_area), 1e-12)
    second_center = np.sum(embeddings * bottom_area[:, None], axis=0) / max(np.sum(bottom_area), 1e-12)
    axis = first_center - second_center
    norm = np.sqrt(np.sum(np.square(axis)))
    if norm < 1e-12:
        return initial
    normal = axis / norm
    center = np.sum(embeddings * node_areas[:, None], axis=0) / max(total, 1e-12)
    centered = embeddings - center
    primary = np.sum(centered * normal, axis=1)
    residual = centered - primary[:, None] * normal
    variance = np.sum(node_areas[:, None] * np.square(residual), axis=0) / max(total, 1e-12)
    probe = int(np.argmax(variance))
    if variance[probe] < 1e-16:
        return initial
    direction = np.sum(residual * (node_areas * residual[:, probe])[:, None], axis=0)
    residual_score = np.sum(residual * direction, axis=1)
    top_near = np.lexsort((primary, 1 - initial))[:max(1, top_count // 5)]
    bottom_near = np.lexsort((-primary, initial))[:max(1, bottom_count // 5)]
    polarity = 1.0 if np.mean(residual_score[top_near]) >= np.mean(residual_score[bottom_near]) else -1.0
    margin = residual_score * polarity
    order_a = np.lexsort((-margin, 1 - initial))
    order_b = np.lexsort((-margin, initial))
    prefix_a = np.cumsum(node_areas[order_a[:top_count]])[:-1]
    prefix_b = np.cumsum(node_areas[order_b[:bottom_count]])[:-1]
    split_a = 1 + int(np.argmin(np.abs(prefix_a - balance_target * np.sum(top_area))))
    split_b = 1 + int(np.argmin(np.abs(prefix_b - (balance_target * total - prefix_a[split_a - 1]))))
    labels = np.maximum(np.argsort(order_a) < split_a, np.argsort(order_b) < split_b)
    if abs(np.sum(node_areas * labels) - balance_target * total) > 0.005 * total:
        return initial
    return labels.astype(np.int64)
# EVOLVE-BLOCK-END
