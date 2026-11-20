"""Join the two roles' decisions to verified physical outcomes from the three C rounds."""
import ast
import hashlib
import json
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
COMPONENTS = {"decoder": "decode_tp_gnn_embeddings", "loss": "compute_tp_gnn_loss"}


def read(path):
    return json.loads(path.read_bytes())


def metrics(receipt):
    rows = receipt["feedback"]["cells"]
    result = {f"{r['case']}/{r['seed']}": r for r in rows}
    assert receipt["status"] == "succeeded" and len(result) == len(rows) == 9
    assert abs(mean(r["score"] for r in rows) - receipt["feedback"]["score"]) < 1e-7
    return result


def implementations(source):
    functions = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef):
            if ast.get_docstring(node, clean=False) is not None:
                node.body = node.body[1:]
            functions[node.name] = ast.dump(node)
    return functions


def report():
    with ZipFile(HERE / "group-c-harness.zip") as archive:
        prior = json.loads(archive.read("prior.json"))["rows"]
    sources = {r["round"]: r["source"] for r in prior}
    control = read(RESULTS / "control.json")
    reference = metrics(control)
    receipts = {r["request_id"]: r for r in (read(p) for p in (RESULTS / "receipts").glob("*.json"))}
    final = read(RESULTS / "c-summary.json")
    assert len(receipts) == final["completed"] == 3
    audit = []
    for n in range(13, 16):
        folder = RESULTS / f"round-{n}"
        p = read(folder / "proposal.json")
        pair = read(folder / "paired-result.json")
        plan, review, checks = p["generator_plan"], p["applied"], p["checks"]
        parent = sources[review["parent_round"]]
        assert hashlib.sha256(parent.encode()).hexdigest() == p["parent_source_sha256"]
        digest = hashlib.sha256(p["source"].encode()).hexdigest()
        assert digest == p["source_sha256"]
        receipt = receipts[f"c{n}-{digest[:36]}"]
        assert hashlib.sha256(receipt["source"].encode()).hexdigest() == receipt["candidate_id"]
        old, new = implementations(parent), implementations(receipt["source"])
        changed = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
        assert changed == [COMPONENTS[review["component"]]]
        assert checks[-1]["verdict"] == "accept" and p["memory_rounds"] == list(range(1, n))
        current = metrics(receipt)
        assert set(current) == set(reference)
        paired = {k: current[k]["score"] - reference[k]["score"] for k in current}
        largest = max(paired, key=paired.get)
        audit.append({
            "round": n, "score": receipt["feedback"]["score"], "candidate_id": receipt["candidate_id"],
            "generator_plan": plan, "supervisor_intervention": review, "code_checks": checks,
            "changed_function": changed[0], "actual_diff": p["diff"], "paired_with_parent": pair,
            "vs_calibrated_r4": {"mean": mean(paired.values()), "by_cell": paired,
                "best_cell": largest, "mean_without_best_cell": mean(v for k, v in paired.items() if k != largest),
                "wins_ties_losses": [sum(v > 1e-6 for v in paired.values()),
                    sum(abs(v) <= 1e-6 for v in paired.values()), sum(v < -1e-6 for v in paired.values())]},
            "case_means": {k: mean(r["score"] for r in current.values() if r["case"] == k)
                           for k in sorted({r["case"] for r in current.values()})}})
        sources[n] = receipt["source"]
    assert max(audit, key=lambda r: r["score"])["round"] == final["best_new"]
    return {"calibrated_r4": control["feedback"]["score"], "rounds": audit}


if __name__ == "__main__":
    data = report()
    (RESULTS / "review.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    for entry in data["rounds"]:
        print(entry["round"], round(entry["score"], 4), entry["vs_calibrated_r4"]["wins_ties_losses"])
