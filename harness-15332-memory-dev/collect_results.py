"""Collect both nine-cell receipts, sources, and the memory actually sent to the model."""

import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import zipfile

from memory import measured_row


def load(path):
    return json.loads(path.read_bytes())


def collect(arm):
    work = arm / "work"
    agent = work / "participant-agent/loss_decoder"
    session = load(work / "session-result.json")
    assert session["status"] == "succeeded" and session["matrix_cells"] == 9
    historical = load(agent / "ten-round-memory.json")
    by_id = {row["candidate_id"]: row for row in historical["rounds"]}
    events = [json.loads(line) for line in (agent / "search.jsonl").read_text().splitlines() if line]
    db = sqlite3.connect("file:"+str(work / "control/budget.sqlite")+"?mode=ro", uri=True)
    evaluations = list(db.execute("select request_id,candidate_id,status from evaluations order by accepted_at"))
    assert len(evaluations) == 2
    report = {"purpose":"development only","ledger":"26016, independent from the completed 15332 ledger",
              "selected_new":session["candidate_id"],"rounds":[]}
    packed = {}
    for i,(rid,cid,status) in enumerate(evaluations, 1):
        assert status == "succeeded"
        proposal = next(e for e in events if e["event"] == "development_proposal" and e["request_id"] == rid)
        pid = proposal["parent_id"]
        parent = by_id[pid]
        folder = work / "evaluations" / rid
        receipt = load(folder / "evaluation_result.json")
        m = receipt["metrics"]
        cells = m["matrix"]["cells"]
        assert len(cells) == 9 and all(c["status"]=="succeeded" and c["valid"] for c in cells)
        n = 10+i
        row = measured_row(n,"26016",cid,pid,m["combined_score"],cells,proposal["changes"],status)
        row["request_id"] = rid
        row["case_means"] = {r["case"]:r["mean"] for r in m["matrix"]["cases"]}
        row["plan"] = proposal["plan"]
        row["parent_round"] = parent["round"]
        row["parent_host"] = parent["host"]
        row["parent_score"] = parent["score"]
        row["score_change_vs_parent"] = row["score"] - parent["score"]
        row["gpu_by_cell"] = {}
        for c in cells:
            k = c["case"] + "/" + str(c["seed"])
            path = folder / "cells" / k / "container/lease.json"
            row["gpu_by_cell"][k] = load(path)["gpus"] if path.exists() else None
        calls = {}
        for e in events:
            if e["event"] != "model_request":
                continue
            inp = json.loads(e["payload"]["input"][-1]["content"])
            memory = inp["memory"]
            if len(memory["rounds"]) != n-1:
                continue
            digest = hashlib.sha256(json.dumps(memory,sort_keys=True).encode()).hexdigest()
            calls.setdefault(e["purpose"], set()).add(digest)
            if e["purpose"]=="development_generation" and inp["parent_id"]==pid:
                parent_source = inp["parent_program"].encode()
                assert hashlib.sha256(parent_source).hexdigest()==parent["source_sha256"]
        assert set(calls)=={"development_plan","development_generation"}
        assert len(set.union(*calls.values()))==1
        row["identical_memory_sha256_both_roles"] = next(iter(calls["development_plan"]))
        row["memory_rounds"] = proposal["memory_rounds"]
        assert row["memory_rounds"] == list(range(1,n))
        src=load(work/"candidates"/cid/"candidate.json")["candidate_files"]["loss_decoder_program.json"]["source"]
        row["source_sha256"]=hashlib.sha256(src.encode()).hexdigest()
        by_id[cid]=row
        report["rounds"].append(row)
        packed["development-%d.py"%i]=src
        packed["development-%d-receipt.json"%i]=json.dumps(receipt,ensure_ascii=False)
    assert session["candidate_id"]==max(report["rounds"],key=lambda row:row["score"])["candidate_id"]
    packed["development-results.json"]=json.dumps(report,indent=2,ensure_ascii=False)
    with zipfile.ZipFile(arm/"development-results.zip","w",zipfile.ZIP_DEFLATED) as z:
        for name,value in packed.items():
            z.writestr(name,value)
    for row in report["rounds"]:
        print(row["round"],row["score"],"parent",row["parent_round"],row["case_means"])


if __name__ == "__main__":
    collect(Path(sys.argv[1]).resolve())
