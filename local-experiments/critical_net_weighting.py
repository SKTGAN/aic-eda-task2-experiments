# EVOLVE-BLOCK-START
def compute_binary_partition_loss(
    probabilities,
    expected_cut,
    net_cut_probabilities,
    net_weights,
    node_features,
    node_areas,
    balance_target,
    cut_weight,
    area_balance_weight,
    binarization_weight,
    epoch,
    max_epochs,
):
    """Mix the original cut objective with bounded critical-net weighting."""
    total_area = node_areas.sum()
    top_area_ratio = (node_areas * probabilities).sum() / total_area
    area_loss = (top_area_ratio - balance_target).square()
    margin_error = (0.9 - (2.0 * probabilities - 1.0).abs()).clamp_min(0.0).square() / 0.81
    binary_loss = (
        0.25 * margin_error.mean()
        + 0.75 * (node_areas * margin_error).sum() / total_area
    )
    criticality = (net_weights / net_weights.mean()).clamp(0.5, 2.0)
    critical_weights = net_weights * criticality
    critical_cut = (critical_weights * net_cut_probabilities).sum() / critical_weights.sum()
    cut_loss = 0.5 * expected_cut + 0.5 * critical_cut
    return (
        cut_weight * cut_loss
        + area_balance_weight * area_loss
        + binarization_weight * binary_loss
    )
# EVOLVE-BLOCK-END
