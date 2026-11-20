"""Verify exactly area-neutral boundary reordering on the measured training embeddings."""
import ast
import csv
import hashlib
import json
import sys

import numpy as np
from replay_capacity_orientation import EXPORT, HERE, PROJECT, get_labels, read_stage
from src.partition.lol.core import load_timing_net_weights, parse_lol_input
from src.partition.lol.methods import tp_gnn as native
from src.partition.lol.methods.tp_gnn_evolution import decode_evolution_embeddings, validate_evolution_source


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    base = json.loads((EXPORT / "three_radius_guard-train.json").read_text())
    geometry = json.loads((EXPORT / "variance-guard-same-loss-nine-cell-geometry.json").read_text())
    by_key = {(r["case"], r["seed"]): r for r in geometry["cells"]}
    methods = {}
    candidate_name = sys.argv[1] if len(sys.argv) > 1 else "overlap_equal_area"
    if candidate_name not in ("overlap_equal_area", "overlap_lloyd", "overlap_neighbors", "overlap_residual"):
        raise ValueError("Expected a geometry candidate using the overlap gate")
    for name in ("three_radius_guard", candidate_name):
        file = HERE / (name + ".py")
        tree = validate_evolution_source(file.read_text(), "tp-gnn-loss-decoder-v1")
        scope = {"__builtins__": {}, "np": np, "int": int, "float": float, "max": max,
                 "min": min, "len": len, "range": range, "abs": abs}
        exec(compile(tree, str(file), "exec"), scope)
        methods[name] = (tree, scope)
    parent, candidate = methods.values()
    assert ast.dump(parent[0].body[0]) == ast.dump(candidate[0].body[0])
    records = []
    for prior in sorted(base["cells"], key=lambda r: (r["case"], -r["seed"])):
        case, seed = prior["case"], prior["seed"]
        stage = read_stage(prior)
        g = by_key[case, seed]
        assert digest(stage / "embeddings.npy") == g["embedding_sha256"]
        ratio = g["rms_radius_sum_over_distance"]
        row = {"case": case, "seed": seed, "radii_over_distance": ratio,
               "embedding_sha256": g["embedding_sha256"]}
        if ratio < 1:
            row.update(final_changed=0, proof="guard false on identical embeddings and native moments")
            records.append(row)
            continue
        emb = np.load(stage / "embeddings.npy")
        groups = [[] for _ in emb]
        areas = np.zeros(len(emb))
        with (stage / "contracted_supernodes.csv").open(encoding="utf-8", newline="") as stream:
            for r in csv.DictReader(stream):
                i = int(r["supernode_id"])
                groups[i].append(r["inst_name"])
                areas[i] += int(r["area"])
        cfg = json.loads((stage / "config.json").read_text())["partition"]
        def decode(scope):
            values, _ = decode_evolution_embeddings(scope, emb, areas, seed,
                cfg["tp_gnn_kmeans_iterations"], cfg["balance_target"], {})
            return np.asarray(values, dtype=np.int8)
        before, after = decode(parent[1]), decode(candidate[1])
        def by_name(labels):
            return {name: ("top" if labels[i] else "bottom") for i, group in enumerate(groups) for name in group}
        assert by_name(before) == get_labels(stage / "decoder_tpgnn_assignment.csv")
        assert np.array_equal(np.sort(areas[before == 1]), np.sort(areas[after == 1]))
        _, instances, nets = parse_lol_input(PROJECT / "official/contest-data/task2/inputs" / case /
                                             "10_floorplan/partition.input")
        native_before = get_labels(stage / "feasible_tpgnn_assignment.csv")
        comparison = native_before
        if np.any(before != after):
            affinities = native.two_center_affinities(emb.tolist(), areas.tolist(), set(np.flatnonzero(after).tolist()))
            name_affinities = {name: affinities[i] for i, group in enumerate(groups) for name in group}
            comparison, report = native.apply_lol_handoff_contract(instances, nets, by_name(after),
                name_affinities, cfg["balance_target"], cfg["balance_tolerance"],
                cfg["macro_count_tolerance"], cfg["macro_area_tolerance"], groups=groups)
            assert report["constraints"]["accepted"]
        row.update(raw_groups_moved=int(np.count_nonzero(before != after)),
                   final_changed=sum(v != native_before[k] for k, v in comparison.items()),
                   identical_top_area_histogram=True,
                   final_sha256=hashlib.sha256(bytes(int(comparison[k] == "top") for k in sorted(comparison))).hexdigest())
        weights_file = stage / "timing_input/timing_net_weights.csv"
        weights = load_timing_net_weights(weights_file, len(nets))
        for name, arrangement in (("current", native_before), ("alternative", comparison)):
            m = native.compute_metrics(instances, nets, arrangement, weights)
            row[name] = {key: m[key] for key in ("cut_net_count", "timing_weighted_cut")}
        print(row, flush=True)
        records.append(row)
    output = {"scope": "Training-only native decoder and legality geometry, no candidate timing scores.",
              "sha256": {name: digest(HERE / (name + ".py")) for name in methods}, "cells": records}
    (EXPORT / (candidate_name.replace("_", "-") + "-vs-three-radius.json")).write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
