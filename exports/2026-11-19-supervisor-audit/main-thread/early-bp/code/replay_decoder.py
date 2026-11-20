"""Replay only the decoder and protected closure on saved local baseline embeddings."""

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


PROJECT = Path(__file__).resolve().parents[2]
TRIAL = {1001: "20261115-161128-780305", 1002: "20261115-205809-358941", 1003: "20261115-213108-753693"}


def load_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return {r["inst_name"]: r["die"] for r in csv.DictReader(stream)}


def difference(before, after):
    if before.keys() != after.keys():
        raise ValueError("Instance or group keys differ")
    direct = sum(before[name] != after[name] for name in before)
    return {"count": len(before), "direct": direct, "flip_adjusted": min(direct, len(before) - direct)}


def run(args):
    official = args.official.resolve()
    place = PROJECT / "official/contest-source/Place-3D"
    sys.path.insert(0, str(place))
    from src.partition.lol.core import parse_lol_input
    from src.partition.lol.methods import tp_gnn as native
    from src.partition.lol.methods.tp_gnn_evolution import validate_evolution_source, decode_evolution_embeddings

    source = args.candidate.read_text(encoding="utf-8")
    official_initial = PROJECT / "official/contest-source/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py"
    initial = official_initial.read_text(encoding="utf-8")
    trees = [validate_evolution_source(text, "tp-gnn-loss-decoder-v1") for text in (initial, source)]
    def loss_body(tree):
        return [ast.dump(node) for node in tree.body[0].body if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Constant)]
    if loss_body(trees[0]) != loss_body(trees[1]):
        raise ValueError("Only unchanged baseline loss is replayable on these fixed embeddings")

    def reference_decoder(embeddings, areas, seed, iterations, target):
        labels, _ = native.area_balanced_weighted_kmeans(embeddings.tolist(), areas.tolist(), seed, iterations, target)
        return np.asarray(labels, dtype=np.int64)

    def decoder(tree):
        namespace = {"np": np, "reference_global_two_way": reference_decoder, "__builtins__": {},
                     "abs": abs, "float": float, "int": int, "len": len, "max": max, "min": min, "range": range}
        exec(compile(tree, "<validated-candidate>", "exec"), namespace, namespace)
        return namespace
    decoders = list(map(decoder, trees))
    _, instances, nets = parse_lol_input(PROJECT / "official/contest-data/task2/inputs/bp-ng45/10_floorplan/partition.input")
    results = []
    for seed, trial in TRIAL.items():
        stage = official / f"contest-work/local-trials/{trial}/baseline/qualification/cells/bp-ng45/{seed}/result/run/20_partition"
        config = json.loads((stage / "config.json").read_text())["partition"]
        points = np.load(stage / "embeddings.npy", allow_pickle=False).tolist()
        groups = [[] for _ in points]
        areas = [0] * len(groups)
        with (stage / "contracted_supernodes.csv").open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                index = int(row["supernode_id"])
                groups[index].append(row["inst_name"])
                areas[index] += int(row["area"])
        if not all(groups) or seed != config["seed"]:
            raise ValueError("Unexpected seed or empty group")
        saved = [load_csv(stage / f) for f in ("decoder_tpgnn_assignment.csv", "feasible_tpgnn_assignment.csv")]
        assignments = []
        closure = []
        for index, namespace in enumerate(decoders):
            labels, _ = decode_evolution_embeddings(namespace, points, areas, seed, config["tp_gnn_kmeans_iterations"], config["balance_target"], {})
            before = {name: ("top" if labels[group_id] == 1 else "bottom") for group_id, group in enumerate(groups) for name in group}
            top = {group_id for group_id, label in enumerate(labels) if label == 1}
            affinity = native.two_center_affinities(points, areas, top)
            by_name = {name: affinity[group_id] for group_id, group in enumerate(groups) for name in group}
            after, report = native.apply_lol_handoff_contract(instances, nets, before, by_name,
                config["balance_target"], config["balance_tolerance"], config["macro_count_tolerance"],
                config["macro_area_tolerance"], groups=groups)
            if index == 0 and (before != saved[0] or after != saved[1]):
                raise ValueError(f"Seed {seed}: replay of official baseline differs from saved artifact: "
                                 f"{difference(saved[0], before)}, {difference(saved[1], after)}")
            if not report["constraints"]["accepted"]:
                raise ValueError(f"Seed {seed}: candidate failed native constraints")
            assignments.append((before, after))
            closure.append({"baseline" if index == 0 else "candidate": report["status"],
                            "cut_nets": report["final_metrics"]["cut_net_count"],
                            "macro_area_error": report["constraints"]["macro_area_error"]})
        seed_result = {"seed": seed, "trial": trial, "baseline_reproduced_exactly": True,
                       "native_closure": closure}
        for index, stage_name in enumerate(("preclosure", "postclosure")):
            before, after = [item[index] for item in assignments]
            seed_result[stage_name] = {"instances": difference(before, after),
                "supernodes": difference({i: before[g[0]] for i,g in enumerate(groups)},
                                         {i: after[g[0]] for i,g in enumerate(groups)})}
        results.append(seed_result)
        print(json.dumps(seed_result), flush=True)
    output = {"diagnostic_only": True, "stage": "partition_only_no_STA",
              "candidate": args.candidate.name, "sha256": hashlib.sha256(source.encode()).hexdigest(), "seeds": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True, help="Native WSL official data with historical local-trials")
    parser.add_argument("--candidate", type=Path, default=Path(__file__).with_name("boundary_decoder.py"))
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
