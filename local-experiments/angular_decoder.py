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
    """Keep the official random-walk embedding objective."""
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Cluster by embedding direction, rounding whole groups by physical area."""
    norms = np.sqrt(np.sum(np.square(embeddings), axis=1, keepdims=True))
    points = embeddings / np.maximum(norms, 1e-12)
    spread = np.sum(np.square(points - np.mean(points, axis=0)), axis=0)
    axis = int(np.argmax(spread))
    top_center = points[np.argmax(points[:, axis])]
    bottom_center = points[np.argmin(points[:, axis])]
    target_area = balance_target * np.sum(node_areas)
    labels = np.zeros_like(node_areas, dtype=np.int64)

    for iteration in range(max_iterations):
        preference = np.sum(points * (top_center - bottom_center), axis=1)
        order = np.argsort(-preference, kind="stable")
        prefix_areas = np.cumsum(node_areas[order])
        split = 1 + int(np.argmin(np.abs(prefix_areas[:-1] - target_area)))
        new_labels = (np.argsort(order) < split).astype(np.int64)
        if np.array_equal(labels, new_labels):
            break
        labels = new_labels

        top_weights = node_areas * labels
        bottom_weights = node_areas * (1 - labels)
        top_sum = np.sum(points * top_weights[:, None], axis=0)
        bottom_sum = np.sum(points * bottom_weights[:, None], axis=0)
        top_center = top_sum / np.maximum(np.sqrt(np.sum(np.square(top_sum))), 1e-12)
        bottom_center = bottom_sum / np.maximum(np.sqrt(np.sum(np.square(bottom_sum))), 1e-12)

    return labels
# EVOLVE-BLOCK-END
