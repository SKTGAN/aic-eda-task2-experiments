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
    """Encourage area balance after thresholding with a smooth surrogate."""
    total_area = node_areas.sum()
    top_area_ratio = (node_areas * probabilities).sum() / total_area
    top_power = probabilities.square().square()
    bottom_power = (1.0 - probabilities).square().square()
    sharpened = top_power / (top_power + bottom_power)
    sharpened_area_ratio = (node_areas * sharpened).sum() / total_area

    # Keep soft balance early and emphasize threshold-aware balance as the
    # host's existing binarization schedule approaches its final weight.
    mix = 0.075 * binarization_weight
    area_loss = (
        (1.0 - mix) * (top_area_ratio - balance_target).square()
        + mix * (sharpened_area_ratio - balance_target).square()
    )
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
