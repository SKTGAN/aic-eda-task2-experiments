"""Read-only excerpts from the official Place-3D TP-GNN decoder."""

import random
from typing import Sequence


def _area_constrained_labels(
    preference: Sequence[float],
    weights: Sequence[float],
    target_area: float,
) -> tuple[list[int], dict]:
    """Round a two-center assignment by the fixed-center fractional order.

    ``preference[i]`` is the reduction in squared distance obtained by placing
    node ``i`` in cluster 1 instead of cluster 0.  Sorting by this value is the
    exact order of the fixed-center fractional relaxation because node area is
    both the clustering weight and capacity.  The deterministic integer
    rounding then keeps an item only when it improves absolute area error.
    """

    order = sorted(range(len(preference)), key=lambda idx: (-preference[idx], idx))
    labels = [0] * len(preference)
    selected_area = 0.0
    for idx in order:
        next_area = selected_area + max(float(weights[idx]), 0.0)
        if abs(next_area - target_area) <= abs(selected_area - target_area):
            labels[idx] = 1
            selected_area = next_area
    return labels, {
        "selected_count": sum(labels),
        "selected_area": selected_area,
        "target_area": target_area,
        "absolute_area_error": abs(selected_area - target_area),
        "rounding": "distance-preference order with deterministic nearest-area integer rounding",
    }


def area_balanced_weighted_kmeans(
    points: list[list[float]],
    weights: Sequence[float],
    seed: int,
    iterations: int,
    balance_target: float,
    allow_empty_clusters: bool = False,
) -> tuple[list[int], dict]:
    """Two-way weighted k-means with an explicit tier-area capacity.

    TP-GNN calls Algorithm 3 weight-balanced, but its printed objective has no
    capacity constraint.  This transparent benchmark completion retains the
    same random initialization and weighted centroids while constraining every
    assignment step to the requested tier area.  The literal Algorithm 3
    result is always emitted separately by :func:`weighted_kmeans`.
    """

    if len(points) <= 1:
        return [0 for _ in points], {
            "iterations": 0,
            "target_area": sum(weights) * balance_target,
            "top_area": 0.0,
            "top_area_ratio": 0.0,
            "absolute_area_error": sum(weights) * balance_target,
        }

    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover - canonical container has NumPy
        raise RuntimeError("area-balanced TP-GNN clustering requires NumPy") from exc

    array = np.asarray(points, dtype=np.float64)
    weight_array = np.maximum(np.asarray(weights, dtype=np.float64), 1.0)
    total_area = float(weight_array.sum())
    target_area = total_area * balance_target
    first, second = random.Random(seed).sample(range(array.shape[0]), 2)
    centers = np.stack([array[first].copy(), array[second].copy()])
    labels = None
    history = []
    converged = False
    for iteration in range(max(1, iterations)):
        distance_0 = np.sum((array - centers[0]) ** 2, axis=1)
        distance_1 = np.sum((array - centers[1]) ** 2, axis=1)
        next_labels, rounding = _area_constrained_labels(
            (distance_0 - distance_1).tolist(),
            weight_array.tolist(),
            target_area,
        )
        next_array = np.asarray(next_labels, dtype=np.int8)
        objective = float(
            np.sum(
                weight_array
                * np.where(next_array == 1, distance_1, distance_0)
            )
        )
        history.append(
            {
                "iteration": iteration + 1,
                "objective": objective,
                "top_area_ratio": rounding["selected_area"] / max(total_area, 1.0),
                "absolute_area_error": rounding["absolute_area_error"],
            }
        )
        if labels is not None and np.array_equal(labels, next_array):
            labels = next_array
            converged = True
            break
        labels = next_array
        for cluster in (0, 1):
            mask = labels == cluster
            if not np.any(mask):
                if allow_empty_clusters:
                    # Spatial bins retain indivisibility failures for their
                    # explicit final area audit instead of losing diagnostics.
                    continue
                raise RuntimeError("area-balanced TP-GNN clustering produced an empty cluster")
            centers[cluster] = np.average(array[mask], axis=0, weights=weight_array[mask])

    top_area = float(weight_array[labels == 1].sum())
    return labels.astype(int).tolist(), {
        "status": "converged" if converged else "max_iterations",
        "iterations": len(history),
        "target_area": target_area,
        "top_area": top_area,
        "top_area_ratio": top_area / max(total_area, 1.0),
        "absolute_area_error": abs(top_area - target_area),
        "algorithm": "capacity-constrained completion of TP-GNN Algorithm 3",
        "assignment_solver": "fixed-center fractional order plus deterministic integer rounding",
        "history": history,
    }
