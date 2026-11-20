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
    """Add a scheduled penalty only for large threshold-area deviations."""
    total_area = node_areas.sum()
    soft_area_ratio = (node_areas * probabilities).sum() / total_area
    soft_area_loss = (soft_area_ratio - balance_target).square()

    top_power = probabilities.square().square()
    bottom_power = (1.0 - probabilities).square().square()
    sharpened = top_power / (top_power + bottom_power)
    sharpened_area_ratio = (node_areas * sharpened).sum() / total_area
    outside_tolerance = ((sharpened_area_ratio - balance_target).abs() - 0.05).clamp_min(0.0)
    area_loss = soft_area_loss + 0.05 * binarization_weight * outside_tolerance.square()

    margin_error = (0.9 - (2.0 * probabilities - 1.0).abs()).clamp_min(0.0).square() / 0.81
    binary_loss = (
        0.25 * margin_error.mean()
        + 0.75 * (node_areas * margin_error).sum() / total_area
    )
    return (
        cut_weight * expected_cut
        + area_balance_weight * area_loss
        + binarization_weight * binary_loss
    )
# EVOLVE-BLOCK-END
