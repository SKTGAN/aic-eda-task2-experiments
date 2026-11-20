"""Prepare the C development archive. Historical training data stays out of the submission tree."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
EX=PROJECT/"exports/2026-11-19-claude-expert-audit/runs"
PREV=PROJECT/"harness-15332-memory-dev"
AUDIT=PROJECT/"exports/2026-11-19-supervisor-audit"

def read(p):return json.loads(p.read_bytes())

def equations(src):
    result={}
    for fn in ast.parse(src).body:
        if isinstance(fn,ast.FunctionDef):
            result[fn.name]="\n".join(ast.unparse(node) for node in fn.body if not isinstance(node,ast.Expr))
    return result

def public_trace(g):
    turns=[]
    for item in g["generation_events"]:
        e=item["event"]
        if e["event"]=="model_response" and e.get("purpose")=="plan":
            turns.append({"role":"planner","visible_reply":str(e.get("output_text",""))[:900]})
        if e["event"] in ("invalid_proposal","plan_discarded","plan_unavailable"):
            turns.append({"event":e["event"],"reason":str(e.get("reason",""))[:220]})
        if e["event"]=="model_request":
            data=json.loads(e["payload"]["input"][-1]["content"])
            turns.append({"role":e.get("purpose"),"inputs":sorted(data),"parent":data.get("parent_id",""),
                          "retry":str(data.get("previous_generation_issue") or "")[:150]})
    return turns

def build():
    rows=read(PREV/"ten-round-memory.json")["rounds"]+read(PREV/"results/development-results.json")["rounds"]
    for r in rows:
        n=r["round"]
        if n<=10:
            folder=EX/"15332-claude-v3"/("round-%02d"%n)
            src=(folder/"candidate.py").read_text(encoding="utf-8")
            matrix=read(folder/"receipt.json")["official_receipt"]["matrix"]; trace=public_trace(read(folder/"generation.json"))
        else:
            src=(PREV/"results"/("development-%d.py"%(n-10))).read_text(encoding="utf-8")
            matrix=read(PREV/"results"/("development-%d-receipt.json"%(n-10)))["metrics"]["matrix"]
            trace=[{"role":"planner","visible_plan":r["plan"]},{"role":"editor","visible_change":r["changes"],
                   "delivered_rounds":r["memory_rounds"],"memory_sha256":r["identical_memory_sha256_both_roles"]}]
        assert hashlib.sha256(src.encode()).hexdigest()==r["source_sha256"]
        r.update(source=src,equations=equations(src),trace=trace,physical=matrix["cells"])
    examples=[]
    for n in (2,4,6):
        folder=EX/"15332-claude-original-34"/("round-%02d"%n)
        d=read(folder/"receipt.json")["overview"]
        examples.append({"version":"Claude34/R%d"%n,"score":d["score"],"parent":d["parent_id"],
                         "functions":equations((folder/"candidate.py").read_text(encoding="utf-8"))})
    for d in read(AUDIT/"main-thread/verified-scores.json"):
        f=AUDIT/"main-thread/development-code"/(d["version"]+".py")
        assert hashlib.sha256(f.read_bytes()).hexdigest()==d["sha256"]
        examples.append({"version":d["version"],"score":d["mean"],"case_means":d["case_means"],
                         "functions":equations(f.read_bytes())})
    raw=json.dumps({"rows":rows,"examples":examples},ensure_ascii=False)
    data=PREV/"dev-harness.zip"
    out=HERE/"group-c-harness.pending"
    with zipfile.ZipFile(data) as original,zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for name in ("parent_harness.py","candidate_reply.py","paired_feedback.py","program.py","editor.md"):
            z.writestr(name,original.read(name))
        z.writestr("prior.json",raw)
        for name in ("agent.py","supervisor.py"):
            z.write(HERE/name,name)
    return out

if __name__=="__main__":build()
