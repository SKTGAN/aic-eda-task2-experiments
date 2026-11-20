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
    """Mechanism: area-weighted spectral bisection of centered embeddings by bounded power iteration on the weighted covariance; Decision: assign each node to the top tier when its rank on the leading projection is at or above the area-cumulative balance split; Prediction: timing-critical cross-tier edges fall and bp-ng45 mean paired score rises on most seeds versus the parent; Falsifier: bp-ng45 mean paired score does not exceed the parent or another case mean falls by more than its tolerance."""
    n = int(embeddings.shape[0])
    d = int(embeddings.shape[1])
    total_area = float(node_areas.sum())
    safe_area = total_area if total_area > 0.0 else 1.0
    areas = node_areas / safe_area
    mean_vec = (embeddings * areas[:, None]).sum(axis=0)
    centered = embeddings - mean_vec[None, :]
    weighted_var = (centered * centered * areas[:, None]).sum(axis=0)
    idx = int(np.argmax(weighted_var))
    direction = (np.arange(d) == idx).astype(np.float64)
    for iteration in range(max_iterations):
        projections = (centered * direction[None, :]).sum(axis=1)
        next_direction = (centered * (areas * projections)[:, None]).sum(axis=0)
        norm_next = float(np.sqrt((next_direction * next_direction).sum()))
        direction = next_direction / norm_next if norm_next > 1e-12 else direction
    scores = (centered * direction[None, :]).sum(axis=1)
    adjusted = scores + 1e-12 * np.arange(n)
    order = np.argsort(adjusted)
    sorted_areas = areas[order]
    cumulative = np.cumsum(sorted_areas)
    target = float(balance_target) * float(cumulative[-1]) if n > 0 else 0.0
    lower_count_raw = int((cumulative < target).sum())
    lower_count = max(1, min(n - 1, lower_count_raw)) if n > 1 else 0
    ranks = np.argsort(np.argsort(adjusted))
    labels = (ranks >= lower_count).astype(np.int64)
    return labels
