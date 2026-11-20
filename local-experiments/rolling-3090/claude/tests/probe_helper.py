"""Test double of the frozen reference decoder helper. Development material only; never in the Agent.

It follows the published excerpt of area_balanced_weighted_kmeans (reference/official_decoder_core.py)
closely enough for contract tests of the probe. Labels it produces are fixture evidence only.
"""

import random


def make_reference(np):
    def reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target):
        points = np.asarray(embeddings, dtype=np.float64)
        weights = np.maximum(np.asarray(node_areas, dtype=np.float64), 1.0)
        target = float(weights.sum()) * balance_target
        first, second = random.Random(seed).sample(range(points.shape[0]), 2)
        centers = np.stack([points[first].copy(), points[second].copy()])
        labels = None
        for _ in range(max(1, int(max_iterations))):
            preference = ((points - centers[0]) ** 2).sum(axis=1) - ((points - centers[1]) ** 2).sum(axis=1)
            order = sorted(range(len(preference)), key=lambda index: (-preference[index], index))
            chosen = np.zeros(points.shape[0], dtype=np.int64)
            area = 0.0
            for index in order:
                if abs(area + weights[index] - target) <= abs(area - target):
                    chosen[index] = 1
                    area += weights[index]
            if labels is not None and np.array_equal(labels, chosen):
                break
            labels = chosen
            for cluster in (0, 1):
                mask = labels == cluster
                if mask.any():
                    centers[cluster] = np.average(points[mask], axis=0, weights=weights[mask])
        return labels
    return reference_global_two_way
