"""Check C's three-round handoff and distinct historical/runtime parent references."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"harness-parent-followup/tests"))
import stubs
from test_loop import Proposer

with tempfile.TemporaryDirectory() as td:
    base=Path(td);agentdir=base/"agent";w=base/"run-c";w.mkdir()
    with zipfile.ZipFile(HERE/"group-c-harness.pending") as z:z.extractall(agentdir)
    stubs.install();sys.path.insert(0,str(agentdir))
    import agent
    from local_tasks.tp_gnn_local_task_definitions import validate_program
    archive=json.loads((agentdir/"prior.json").read_text())
    rows=archive["rows"];r4=rows[3]
    assert len(rows)==12 and all(len(r["physical"])==9 for r in rows)
    assert len(archive["examples"])==7
    pp=base/"control-r4/receipts";pp.mkdir(parents=True)
    start=validate_program(r4["source"],agent.DECODER_TASK)
    calibrated=[dict(c, score=c["score"]-27) for c in r4["physical"]]
    calibration=round(sum(c["score"] for c in calibrated)/len(calibrated),4)
    agent.save(pp/"initial.json",{"candidate_id":agent.digest(start),"feedback":{"cells":calibrated},"status":"succeeded"})
    task=base/"framework/local_tasks"/agent.DECODER_TASK;task.mkdir(parents=True);(task/"prompt.md").write_text("Mock legal interface")
    proposer=Proposer();events=[];sub=[]
    def reply(payload):
        sysmsg,request=[m["content"] for m in payload["input"]];p=json.loads(request);n=13+len(sub)
        cell="ariane133-ng45/1002"
        if sysmsg.startswith("Act as the C"):
            assert len(p["history"]["rounds"])==n-1
            assert p["history"]["rounds"][-1]["round"]==n-1
            events.append(("plan",n))
            assert p["history"]["rounds"][3]["score"]==calibration
            assert p["history"]["rounds"][3]["archived_other_host"]["score"]==round(r4["score"],4)
            return stubs.completed(json.dumps(dict(parent_round=4,component="decoder",target_cell=cell,
                   parent_mean_on_C=calibration,protect_cell=cell,hypothesis="mock",prediction="mock",falsifier="mock")))
        if sysmsg.startswith("You supervise"):
            events.append(("audit",n))
            return stubs.completed(json.dumps(dict(parent_round=4,parent_mean_on_C=calibration,component="loss",target_cell=cell,protect_cell=cell,
                  evidence=[dict(round=4,cell=cell),dict(round=n-1,cell=cell)],correction="mock correction",prediction="up",falsifier="down")))
        if sysmsg.startswith("Independently review"):
            assert "generator_proposal" not in p and p["reviewer_correction"]["component"]=="loss"
            reject=n==13 and ("check",n) not in events
            events.append(("check",n))
            return stubs.completed(json.dumps({"verdict":"revise" if reject else "accept","finding":"mock",
                                               "required_change":"refine"}))
        assert p["search_intent"]=="loss_only" and p["parent_program"]==r4["source"]
        assert p["reviewer_correction"]["component"]=="loss"
        events.append(("edit",n));return proposer(None,sysmsg,p)
    def evaluate(source,rid):
        sub.append(rid)
        return {"source":source,"candidate_id":hashlib.sha256(source.encode()).hexdigest(),"status":"succeeded",
                "feedback":{"score":r4["score"],"cells":r4["physical"]}}
    ctx=SimpleNamespace(model=SimpleNamespace(responses_create=reply),files={"workspaces":str(w/"workspaces"),
                        "framework":str(base/"framework")},submit_evaluation=evaluate)
    agent.Agent().run(ctx)
    assert len(sub)==3 and len(set(sub))==3
    assert len([e for e in events if e[0]=="check"])==4
    assert json.loads((w/"c-summary.json").read_text())["completed"]==3
    for n in range(13,16):
        h=json.loads((w/("round-%02d"%n)/"proposal.json").read_text())
        assert h["memory_rounds"]==list(range(1,n)) and h["checks"][-1]["verdict"]=="accept"
    print("Verified R13-R15 with 12-14 prior rounds, real nine-cell archive, reviewer-overridden scope, revision, and three unique submissions.")
