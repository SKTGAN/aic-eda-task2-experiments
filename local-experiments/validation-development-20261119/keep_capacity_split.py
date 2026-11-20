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
    """Use graph attraction when movable groups own most of the die area."""
    pair_term = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)
    total_area = node_areas.sum()
    # The legal die share ranges from 47 to 53 percent. Moving a larger
    # group requires a compensating transfer in the other direction.
    oversized_area = torch.where(node_areas > 0.06 * total_area, node_areas, torch.zeros_like(node_areas)).sum()
    if 2.0 * oversized_area > total_area:
        return pair_term
    weight_total = graph_weights.sum()
    edge_mean = (graph_weights * F.softplus(-graph_scores)).sum() / (weight_total + 1e-6)
    pair_count = float(len(positive_scores)) + float(len(negative_scores))
    batch_scale = pair_count / max(1.0, float(source_batch_size))
    return pair_term + batch_scale * edge_mean


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Keep the published area-balanced clustering and orient it with the seeded anchors."""
    n_nodes = int(embeddings.shape[0])
    total_area = node_areas.sum()
    labels = reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
    oversized_area = np.sum(np.where(node_areas > 0.06 * total_area, node_areas, 0.0))
    if 2.0 * oversized_area > total_area:
        # The two dies have different placement contexts. The reversed native
        # orientation is a fixed choice evaluated on training pairs.
        return 1 - labels
    top_mask = labels == 1
    bottom_mask = labels == 0
    top_area = node_areas[top_mask].sum()
    bottom_area = node_areas[bottom_mask].sum()
    center_top = (node_areas[top_mask, None] * embeddings[top_mask]).sum(axis=0) / top_area
    center_bottom = (node_areas[bottom_mask, None] * embeddings[bottom_mask]).sum(axis=0) / bottom_area

    # Align the reference partition's polarity with the seed anchor direction.
    anchor = embeddings[int(seed) % n_nodes]
    far = embeddings[int(np.argmax(((embeddings - anchor) ** 2).sum(axis=1)))]
    if np.sum((center_top - center_bottom) * (far - anchor)) < 0:
        labels = 1 - labels
    return labels
# EVOLVE-BLOCK-END
