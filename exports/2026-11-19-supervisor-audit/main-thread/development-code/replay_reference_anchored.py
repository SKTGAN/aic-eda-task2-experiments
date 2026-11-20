"""Compare an oriented official reference and capacity decoder to the local champion."""
import csv
import hashlib
import json

import numpy as np
from replay_capacity_orientation import EXPORT, HERE, PROJECT, get_labels, read_stage
from src.partition.lol.core import load_timing_net_weights, parse_lol_input
from src.partition.lol.methods import tp_gnn as native
from src.partition.lol.methods.tp_gnn_evolution import decode_evolution_embeddings, validate_evolution_source


def labels_by_name(groups, labels):
    return {name: ("top" if labels[i] else "bottom") for i, names in enumerate(groups) for name in names}


def physical_replay(row, source):
    case, seed = row["case"], row["seed"]
    stage = read_stage(row)
    with (stage / "embeddings.npy").open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    emb = np.load(stage / "embeddings.npy", mmap_mode="r")
    groups = [[] for _ in emb]
    areas = np.zeros(len(emb))
    parent_by_name = get_labels(stage / "decoder_tpgnn_assignment.csv")
    with (stage / "contracted_supernodes.csv").open(encoding="utf-8", newline="") as stream:
        for r in csv.DictReader(stream):
            i = int(r["supernode_id"])
            groups[i].append(r["inst_name"])
            areas[i] += int(r["area"])
    cfg = json.loads((stage / "config.json").read_text())["partition"]
    audit = {"case": case, "seed": seed, "embedding_sha256": sha}
    def reference(points, weights, seed, iterations, target):
        # Pass arrays directly: the official routine immediately coerces lists to float64 arrays.
        values, report = native.area_balanced_weighted_kmeans(points, weights, seed, iterations, target)
        labels = np.array(values)
        anchor = points[seed % len(points)]
        far = points[np.argmax(((points - anchor) ** 2).sum(axis=1))]
        axis = np.average(points[labels == 1], weights=weights[labels == 1], axis=0)
        axis -= np.average(points[labels == 0], weights=weights[labels == 0], axis=0)
        audit["reference_flipped_to_align"] = bool(axis @ (far - anchor) < 0)
        audit["reference_iterations"] = report["iterations"]
        return labels
    scope = {"__builtins__": {}, "np": np, "abs": abs, "float": float, "int": int,
             "len": len, "max": max, "min": min, "range": range, "reference_global_two_way": reference}
    tree = validate_evolution_source(source, "tp-gnn-loss-decoder-v1")
    exec(compile(tree, "anchored_reference", "exec"), scope)
    raw, _ = decode_evolution_embeddings(scope, emb, areas, seed, cfg["tp_gnn_kmeans_iterations"], cfg["balance_target"], {})
    compared = labels_by_name(groups, raw)
    changed = sum(v != parent_by_name[k] for k,v in compared.items())
    audit["raw_instances_changed"] = changed
    audit["raw_groups_changed"] = sum(compared[g[0]] != parent_by_name[g[0]] for g in groups)
    final_parent = get_labels(stage / "feasible_tpgnn_assignment.csv")
    final_candidate = final_parent
    if changed:
        _, instances, nets = parse_lol_input(PROJECT / "official/contest-data/task2/inputs" / case /
                                             "10_floorplan/partition.input")
        # The official closure only reads affinities if repair is necessary.
        def close(affinities):
            return native.apply_lol_handoff_contract(instances, nets, compared, affinities, cfg["balance_target"],
                cfg["balance_tolerance"], cfg["macro_count_tolerance"], cfg["macro_area_tolerance"], groups=groups)
        # Official repair implementations may use dict.get defaults, so always compute real margins.
        affinities = native.two_center_affinities(emb, areas, set(np.flatnonzero(raw).tolist()))
        by_name = {name: affinities[i] for i, g in enumerate(groups) for name in g}
        final_candidate, rep = close(by_name)
        assert rep["constraints"]["accepted"]
        weights = load_timing_net_weights(stage / "timing_input/timing_net_weights.csv", len(nets))
        for name, assn in (("parent", final_parent), ("candidate", final_candidate)):
            metrics = native.compute_metrics(instances, nets, assn, weights)
            audit[name] = {key: metrics[key] for key in ("cut_net_count", "timing_weighted_cut")}
    audit["final_changed"] = sum(v != final_parent[k] for k, v in final_candidate.items())
    audit["flip_adjusted"] = min(audit["final_changed"], len(final_parent) - audit["final_changed"])
    audit["instance_count"] = len(final_parent)
    audit["final_labels_sha256"] = hashlib.sha256(bytes(int(final_candidate[k] == "top") for k in sorted(final_candidate))).hexdigest()
    return audit


def main():
    card = json.loads((EXPORT / "three_radius_guard-train.json").read_text())
    candidate = HERE / "reference_anchored_capacity.py"
    output = {"scope": "Reference decoder on archived training embeddings, legal partition geometry only.",
              "candidate": hashlib.sha256(candidate.read_bytes()).hexdigest(),
              "parent": card["candidate_sha256"], "cells": []}
    target = EXPORT / "reference-anchored-capacity-vs-three-radius.json"
    for row in sorted(card["cells"], key=lambda r: (r["case"] != "bp-ng45", r["seed"])):
        if row["case"] == "bp_fe-ng45":
            continue
        found = physical_replay(row, candidate.read_text())
        output["cells"].append(found)
        print(found, flush=True)
        target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
