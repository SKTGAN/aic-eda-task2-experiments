"""Replay the predeclared layer-orientation rule on existing training embeddings."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
EXPORT = PROJECT / "exports/2026-11-18-local-score-challenge"
REMOTE = Path(r"\\wsl.localhost\Ubuntu")
sys.path.insert(0, str(PROJECT / "official/contest-source/Place-3D"))
from src.partition.lol.core import parse_lol_input
from src.partition.lol.methods import tp_gnn as native
from src.partition.lol.methods.tp_gnn_evolution import decode_evolution_embeddings, validate_evolution_source


def get_labels(path):
    with path.open(newline="", encoding="utf-8") as f:
        return {r["inst_name"]: r["die"] for r in csv.DictReader(f)}


def read_stage(row):
    return (REMOTE / row["receipt"].lstrip("/")).parent / "cells" / row["case"] / str(row["seed"]) / "result/run/20_partition"


def orientation(labels, areas):
    scaled = areas / areas.max()
    top, bottom = (scaled[labels == i] for i in (1, 0))
    concentrations = [(v ** 2).sum() / v.sum() for v in (top, bottom)]
    flip = concentrations[0] < concentrations[1]
    return (1-labels if flip else labels), list(map(float, concentrations)), bool(flip)


def replay():
    names = ("capacity_quantum", "variance_guard")
    decoders, loss_trees = {}, []
    import ast
    for n in names:
        file = HERE / (n + ".py")
        tree = validate_evolution_source(file.read_text(), "tp-gnn-loss-decoder-v1")
        loss_trees.append(ast.dump(tree.body[0]))
        namespace = {"np": np}
        exec(compile(tree, str(file), "exec"), namespace)
        decoders[n] = namespace
    assert len(set(loss_trees)) == 1
    oriented_decoder = None
    oriented_source = HERE / "guard_orientation.py"
    if oriented_source.is_file():
        candidate_tree = validate_evolution_source(oriented_source.read_text(), "tp-gnn-loss-decoder-v1")
        assert ast.dump(candidate_tree.body[0]) == loss_trees[1]
        oriented_decoder = {"np": np}
        exec(compile(candidate_tree, str(oriented_source), "exec"), oriented_decoder)
    physical = {n: json.loads((EXPORT / (n + "-train.json")).read_text()) for n in names}
    assert len(physical[names[0]]["cells"]) == 9
    guard_scores = {(i["case"], i["seed"]):i for i in physical[names[1]]["cells"]}
    rows=[]
    case_cache={}
    for row in sorted(physical[names[0]]["cells"],key=lambda r:(r["case"],r["seed"])):
        c, seed = row["case"], row["seed"]
        assert c in {"bp-fe-ng45", "bp_fe-ng45", "bp-ng45", "ariane133-ng45"} and seed in (1001,1002,1003)
        stage = read_stage(row)
        cfg = json.loads((stage/"config.json").read_text())["partition"]
        emb = np.load(stage/"embeddings.npy", allow_pickle=False)
        groups = [[] for _ in range(len(emb))]
        areas = np.zeros(len(emb))
        with (stage/"contracted_supernodes.csv").open(newline="",encoding="utf-8") as f:
            for v in csv.DictReader(f):
                i=int(v["supernode_id"])
                groups[i].append(v["inst_name"])
                areas[i]+=int(v["area"])
        assert cfg["seed"] == seed and np.all(areas > 0)
        if c not in case_cache:
            _, instances, nets = parse_lol_input(PROJECT/"official/contest-data/task2/inputs"/c/"10_floorplan/partition.input")
            case_cache[c]=instances,nets
        instances,nets=case_cache[c]
        ordered_names = [name for g in groups for name in g]
        code = lambda a: np.array([a[name]=="top" for name in ordered_names],dtype=np.int8)
        def name_map(labels):
            return {name:("top" if labels[i] else "bottom") for i,g in enumerate(groups) for name in g}
        cache={}
        points, weights = emb.tolist(),areas.tolist()
        def closed(labels):
            key = labels.astype(np.int8).tobytes()
            if key not in cache:
                margin=native.two_center_affinities(points, weights, set(np.flatnonzero(labels).tolist()))
                by_name={name:margin[i] for i,g in enumerate(groups) for name in g}
                fixed, rep=native.apply_lol_handoff_contract(instances,nets,name_map(labels),by_name,
                    cfg["balance_target"],cfg["balance_tolerance"],cfg["macro_count_tolerance"],
                    cfg["macro_area_tolerance"],groups=groups)
                assert rep["constraints"]["accepted"]
                cache[key]=code(fixed)
            return cache[key]
        out={"case":c,"seed":seed,"embedding_origin":str(row["receipt"]),"parents":{}}
        potential={}
        for n in names:
            raw,_=decode_evolution_embeddings(decoders[n],emb,areas,seed,cfg["tp_gnn_kmeans_iterations"],cfg["balance_target"],{})
            labels=np.asarray(raw,dtype=np.int8)
            actual = stage if n==names[0] else (read_stage(guard_scores[c,seed]) if (c,seed) in guard_scores else None)
            if actual is not None and (actual/"decoder_tpgnn_assignment.csv").is_file():
                assert name_map(labels)==get_labels(actual/"decoder_tpgnn_assignment.csv")
                cache[labels.tobytes()]=code(get_labels(actual/"feasible_tpgnn_assignment.csv"))
            orient, concentration, flipped=orientation(labels,areas)
            if n == "variance_guard" and oriented_decoder is not None:
                produced, _ = decode_evolution_embeddings(oriented_decoder, emb, areas, seed,
                    cfg["tp_gnn_kmeans_iterations"], cfg["balance_target"], {})
                assert np.array_equal(produced, orient)
            before,after=closed(labels),closed(orient)
            changed=int(np.count_nonzero(before!=after))
            out["parents"][n]={"flip":flipped,"concentration_top_bottom":concentration,"instance_count":len(before),
                               "postclosure_changed":changed,"postclosure_change_excluding_flip":min(changed,len(before)-changed),
                               "sha256_labels":hashlib.sha256(after.tobytes()).hexdigest(),
                               "confirmed_physical_parent_assignments":bool(actual is not None and (actual/"feasible_tpgnn_assignment.csv").is_file())}
            potential[n]=after
        out["oriented_children_differ"]=int(np.count_nonzero(potential[names[0]]!=potential[names[1]]))
        rows.append(out)
        print(c,seed,[(k,d["flip"],d["postclosure_changed"]) for k,d in out["parents"].items()],out["oriented_children_differ"],flush=True)
        result={"scope":"Local training only, decoder/official closure replay on frozen embeddings. No physical timing estimated.",
                "guard_oriented_program_sha256":hashlib.sha256(oriented_source.read_bytes()).hexdigest() if oriented_decoder is not None else None,
                "complete":len(rows)==9,"cells":rows}
        destination=EXPORT/"capacity-and-guard-orientation-replay.json"
        temp=destination.with_suffix(".tmp"); temp.write_text(json.dumps(result,indent=2)+"\n");temp.replace(destination)


if __name__ == "__main__":
    replay()
