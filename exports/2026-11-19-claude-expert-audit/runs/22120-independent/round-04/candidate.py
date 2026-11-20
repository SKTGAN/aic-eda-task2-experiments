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
    """Keep the parent random-walk contrastive objective unchanged.

    Relative to the parent program this loss body is byte-equivalent in
    behaviour: the same logistic positive-pair attraction and logistic
    negative-pair separation, normalized by the source batch size. It is
    kept fixed so that the paired comparison isolates the decoder change.
    """
    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Decode on mean-removed embedding geometry with a balanced margin sweep.

    Change versus the parent program: the parent delegates the whole design
    split to ``reference_global_two_way`` (raw L2-normalized geometry, seeded
    two-center initialization, nearest-center rounding). Here the physical
    area-weighted mean embedding is subtracted first, so the common-mode
    direction that dominates the raw space no longer drives the split. The
    two centers are initialized from an area-balanced cut along the highest
    weighted-variance contrast axis, then refined by a bounded balanced
    two-means loop whose assignment is an area-cumulative sweep of the
    center-margin ranking (whole supernodes only).

    Expected measurable effect: the discrete die partition changes on cells
    where the raw two-means cut was carried by the shared embedding mode, so
    the frozen closure, placement, HBT assignment and STA see a genuinely
    different grouping and the measured WNS/TNS move away from the parent.
    Invalidation: if the emitted labels reproduce the parent helper on most
    cells (partition mostly unchanged / orientation only), or the official
    combined score stays inside the parent's per-cell spread, the
    common-mode-removal hypothesis is rejected.
    """
    n = int(embeddings.shape[0])
    total_area = node_areas.sum()
    denom_total = np.where(total_area > 0.0, total_area, 1.0)
    weights = node_areas / denom_total
    weight_col = weights[:, None]

    mean_vec = (embeddings * weight_col).sum(axis=0)
    centered = embeddings - mean_vec

    variance = (weight_col * centered * centered).sum(axis=0)
    axis = int(np.argmax(variance))
    proj = centered[:, axis]

    target_area = balance_target * denom_total
    order = np.argsort(proj)
    cum = np.cumsum(node_areas[order])
    count_low = int(np.sum(cum < target_area))
    count_low = max(1, min(count_low, n - 1))
    rank = np.argsort(np.argsort(proj))
    low_mask = rank < count_low

    low_sel = np.where(low_mask, weights, 0.0)
    high_sel = np.where(low_mask, 0.0, weights)
    sum_low = low_sel.sum()
    sum_high = high_sel.sum()
    den_low = np.where(sum_low > 0.0, sum_low, 1.0)
    den_high = np.where(sum_high > 0.0, sum_high, 1.0)
    center_low = (centered * low_sel[:, None]).sum(axis=0) / den_low
    center_high = (centered * high_sel[:, None]).sum(axis=0) / den_high

    labels = np.where(low_mask, 0.0, 1.0)
    for step in range(max_iterations):
        sel_low = np.where(labels < 0.5, weights, 0.0)
        sel_high = np.where(labels < 0.5, 0.0, weights)
        mass_low = sel_low.sum()
        mass_high = sel_high.sum()
        norm_low = np.where(mass_low > 0.0, mass_low, 1.0)
        norm_high = np.where(mass_high > 0.0, mass_high, 1.0)
        center_low = (centered * sel_low[:, None]).sum(axis=0) / norm_low
        center_high = (centered * sel_high[:, None]).sum(axis=0) / norm_high

        diff_low = centered - center_low
        diff_high = centered - center_high
        d_low = (diff_low * diff_low).sum(axis=1)
        d_high = (diff_high * diff_high).sum(axis=1)
        margin = d_low - d_high

        m_order = np.argsort(margin)
        m_cum = np.cumsum(node_areas[m_order])
        count_top = int(np.sum(m_cum < target_area))
        count_top = max(1, min(count_top, n - 1))
        m_rank = np.argsort(np.argsort(margin))
        top_mask = m_rank >= (n - count_top)
        labels = np.where(top_mask, 1.0, 0.0)

    return np.where(labels < 0.5, 0, 1)
