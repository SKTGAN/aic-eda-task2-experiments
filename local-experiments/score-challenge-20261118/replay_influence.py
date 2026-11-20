"""Check if a cluster variance guard survives removal of any single supernode."""
import csv
import json

import numpy as np

from replay_capacity_orientation import EXPORT, get_labels, read_stage


def read_groups(stage):
    embeddings = np.load(stage / "embeddings.npy", mmap_mode="r")
    instance_labels = get_labels(stage / "decoder_tpgnn_assignment.csv")
    areas = np.zeros(len(embeddings))
    labels = np.full(len(embeddings), -1, dtype=np.int8)
    with (stage / "contracted_supernodes.csv").open(encoding="utf-8", newline="") as source:
        for item in csv.DictReader(source):
            i = int(item["supernode_id"])
            areas[i] += int(item["area"])
            side = int(instance_labels[item["inst_name"]] == "top")
            assert labels[i] in (-1, side)
            labels[i] = side
    assert np.all(areas > 0) and np.all(labels >= 0)
    return embeddings, areas, labels


def components(points, weights, side):
    sums = np.zeros((2, points.shape[1]))
    for start in range(0, len(points), 512):
        block = slice(start, start + 512)
        for k in (0, 1):
            sums[k] += np.einsum("i,ij->j", weights[block] * (side[block] == k), points[block])
    center = sums.sum(axis=0) / weights.sum()
    centroids = sums / np.bincount(side, weights=weights)[:, None]
    global_residual, local_residual = np.zeros(len(points)), np.zeros(len(points))
    for start in range(0, len(points), 512):
        block = slice(start, start + 512)
        global_residual[block] = ((points[block] - center) ** 2).sum(axis=1)
        local_residual[block] = ((points[block] - centroids[side[block]]) ** 2).sum(axis=1)
    return global_residual, local_residual


def main():
    guard = json.loads((EXPORT / "variance_guard-train.json").read_text())
    physical = {(r["case"], r["seed"]): r for r in guard["cells"]}
    audited = json.loads((EXPORT / "variance-guard-same-loss-nine-cell-geometry.json").read_text())
    rows = []
    for cell in audited["cells"]:
        if cell["branch"] != "claude_r4":
            rows.append({"case": cell["case"], "seed": cell["seed"], "choose_r4": False,
                         "reason": "ordinary separation is already below within-cluster variance"})
            continue
        points, weights, labels = read_groups(read_stage(physical[cell["case"], cell["seed"]]))
        global_res, local_res = components(points, weights, labels)
        mass = weights.sum()
        by_side = np.bincount(labels, weights=weights)
        corrected_total = weights @ global_res - weights * (mass / (mass - weights)) * global_res
        corrected_within = weights @ local_res - weights * (by_side[labels] / (by_side[labels] - weights)) * local_res
        ratios = corrected_total / corrected_within - 1.0
        i = int(np.argmin(ratios))
        test_weights = weights.copy()
        test_weights[i] = 0.0
        ref_g, ref_l = components(points, test_weights, labels)
        check = (test_weights @ ref_g) / (test_weights @ ref_l) - 1.0
        assert np.isclose(ratios[i], check)
        assert np.isclose((weights @ global_res) / (weights @ local_res) - 1.0, cell["variance_ratio_between_over_within"])
        row = {"case": cell["case"], "seed": cell["seed"],
               "ordinary_between_over_within": float((weights @ global_res) / (weights @ local_res) - 1.0),
               "minimum_leave_one_out_between_over_within": float(ratios[i]),
               "choose_r4": bool(np.all(ratios >= 1.0))}
        print(row, flush=True)
        rows.append(row)
    (EXPORT / "leave-one-supernode-out-geometry.json").write_text(json.dumps({
        "scope": "training embeddings only, no timing consulted in this replay",
        "rule": "keep separated clusters only if between variance also exceeds within variance after every single supernode deletion",
        "cells": rows}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
