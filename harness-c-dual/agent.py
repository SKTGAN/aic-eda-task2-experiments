"""C development experiment. A generator and a separate evidence reviewer share physical receipts."""
import hashlib
import json
from pathlib import Path
from statistics import mean

from candidate_reply import generated_program,model_text
from parent_harness import ask_model,candidate_gate,function_keys,proposal_keys,UNCHANGED_FUNCTION,DECODER_TASK
from supervisor import AUDITOR,CHECK,DOMAIN,PLANNER,body,change,check_plan,obj,packed_cells,packet

HERE=Path(__file__).resolve().parent

def digest(s):return hashlib.sha256(s.encode()).hexdigest()

def save(path,data):
    tmp=path.with_suffix(".pending")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)

def json_turn(ctx,purpose,instructions,request,check):
    last=""
    for effort in ("high","medium","low"):
        try:
            reply=ask_model(ctx,instructions,{**request,"format_feedback":last},effort,purpose)
            return check(obj(model_text(reply)))
        except (ValueError,TypeError) as err:
            last=str(err)[:400]
    raise ValueError(purpose+" could not produce a valid response: "+last)

def verdict(value):
    if value.get("verdict") not in ("accept","revise") or not value.get("finding"):
        raise ValueError("Provide verdict and a concrete finding")
    if value["verdict"]=="revise" and not value.get("required_change"):raise ValueError("State the required change")
    return value

def lessons(examples):
    # Pair references are read-only development evidence. No referenced program is automatically submitted.
    return [{"version":e["version"],"training_score":e["score"],"case_means":e.get("case_means"),
             "edited_loss":e["functions"]["compute_tp_gnn_loss"][:900] if e["version"].startswith("Claude") else None,
             "decoder_delta":change_functions(examples[i-1],e) if i>0 and i!=3 else None}
            for i,e in enumerate(examples)]

def change_functions(a,b):
    import difflib
    key="decode_tp_gnn_embeddings"
    return "\n".join(difflib.unified_diff(a["functions"][key].splitlines(),b["functions"][key].splitlines(),n=1,lineterm=""))[:1550]

def mitigation(rows,control,n,receipt,h):
    parent=next(r for r in rows if r["round"]==h["applied"]["parent_round"])
    measured=packed_cells(receipt["feedback"]["cells"])
    p_same=parent["round"]==4 or parent["host"]=="C"
    baseline=control if parent["round"]==4 else packed_cells(parent["physical"])
    paired={k:round(v[0]-baseline[k][0],4) for k,v in measured.items() if k in baseline and v[0] is not None and baseline[k][0] is not None}
    advice=h["applied"]
    return {"round":n,"comparison_same_layout":p_same,"parent_round":parent["round"],
            "protect_cell":advice["protect_cell"],"protect_delta":paired.get(advice["protect_cell"]),
            "target_cell":advice["target_cell"],"target_delta":paired.get(advice["target_cell"]),
            "mean_delta":mean(paired.values()) if len(paired)==9 else None,"paired":paired}

class Agent:
    def run(self,ctx):
        prior=json.loads((HERE/"prior.json").read_text())
        rows=prior["rows"]
        assert [r["round"] for r in rows]==list(range(1,13))
        ids={r["candidate_id"]:r["round"] for r in rows}
        for row in rows:
            row["parent_round"]=ids.get(row["parent_id"],"start")
            assert digest(row["source"])==row["source_sha256"]
        work=Path(ctx.files["workspaces"]).parent
        receipt=json.loads((work.parent/"control-r4/receipts/initial.json").read_text())
        from local_tasks.tp_gnn_local_task_definitions import validate_program
        if receipt["candidate_id"]!=digest(validate_program(rows[3]["source"],DECODER_TASK)):
            raise ValueError("Same-layout control does not match the exact historical R4 program")
        control=packed_cells(receipt["feedback"]["cells"])
        if len(control)!=9 or receipt["status"]!="succeeded":raise ValueError("Incomplete C control")
        reference=lessons(prior["examples"])
        guide=(Path(ctx.files["framework"])/"local_tasks"/DECODER_TASK/"prompt.md").read_text()
        editor=(HERE/"editor.md").read_text().split("## Offline Expert Knowledge")[0]
        seen={function_keys(r["source"]) for r in rows}
        for n in range(13,16):
            out=work/("round-%02d"%n);out.mkdir(exist_ok=True)
            bundle=out/"proposal.json"
            history=packet(rows,control)
            if not bundle.is_file():
                def plancheck(v):return check_plan(v,rows,control)
                def auditcheck(v):return check_plan(v,rows,control,True)
                calibration = (" Include parent_mean_on_C in the JSON. Copy it from history.same_layout_mean_by_parent "
                    "for your selected parent; use null if that parent has not been measured here. "
                    "Use that mean and its C cells to set thresholds. Archived scores belong to different machines. "
                    "All nine fixed cells are always evaluated. A target is a diagnostic comparison only.")
                draft=json_turn(ctx,"generator_plan",PLANNER+calibration+"\n"+DOMAIN,
                                {"history":history,"development_references":reference},plancheck)
                chosen=next(r for r in rows if r["round"]==draft["parent_round"])
                sup=json_turn(ctx,"supervisor_intervention",AUDITOR+calibration+"\n"+DOMAIN,
                       {"history":history,"generator_proposal":draft,"proposed_parent_source":chosen["source"],
                        "development_references":reference},auditcheck)
                parent=next(r for r in rows if r["round"]==sup["parent_round"])
                intent=sup["component"]+"_only"
                public={"search_intent":intent,"parent_id":parent["candidate_id"],"parent_program":parent["source"],
                        "reviewer_correction":sup,"history":history}
                checks=[]
                source=None
                for cycle in range(4):
                    last=""
                    for effort in ("medium","low","low","low"):
                        response=ask_model(ctx,editor+"\nImplement the reviewer's corrected experiment within the declared component.\n"+guide,
                            {**public,"previous_generation_issue":last,"prior_code_review":checks[-1] if checks else None,
                             "draft_for_revision":source},"low" if effort=="low" else "medium","generator_code")
                        try:
                            proposed=generated_program(response)
                            proposal_keys(proposed,function_keys(parent["source"]),UNCHANGED_FUNCTION[intent],seen)
                            candidate_gate(proposed)
                            source=proposed;break
                        except (ValueError,SyntaxError) as err:last=str(err)[:400]
                    else:raise ValueError("No legal distinct proposal: "+last)
                    review=json_turn(ctx,"supervisor_code_check",CHECK+" Only the applied review contract is active. "
                        "You review editable executable code. Cell names, score thresholds and reporting targets "
                        "belong to the coordinator, which has already adopted the applied contract. Do not request "
                        "edits to proposal metadata, documentation or the fixed nine-cell evaluation roster.",
                        {"reviewer_correction":sup,
                         "parent_implementation":body(parent["source"]),"executable_diff":change(parent["source"],source),
                         "actual_source":source,"previous_review":checks[-1] if checks else None},verdict)
                    checks.append(review)
                    if review["verdict"]=="accept":break
                else:raise ValueError("The independent reviewer did not accept the revised program")
                h={"round":n,"memory_rounds":[r["round"] for r in rows],"history_sha256":digest(json.dumps(history,sort_keys=True)),
                   "generator_plan":draft,"applied":sup,"checks":checks,"parent_id":parent["candidate_id"],
                   "parent_source_sha256":digest(parent["source"]),"source":source,"source_sha256":digest(source),
                   "diff":change(parent["source"],source)}
                save(bundle,h)
            else:h=json.loads(bundle.read_text())
            rid="c%02d-"%n+h["source_sha256"][:36]
            seen.add(function_keys(h["source"]))
            receipt=ctx.submit_evaluation(h["source"],rid)
            if receipt["status"]!="succeeded":raise RuntimeError("Incomplete nine-cell physical receipt for "+rid)
            result=mitigation(rows,control,n,receipt,h)
            save(out/"paired-result.json",result)
            cells=receipt["feedback"]["cells"]
            rows.append({"round":n,"host":"C","parent_round":h["applied"]["parent_round"],"source":receipt["source"],
                 "candidate_id":receipt["candidate_id"],"source_sha256":digest(receipt["source"]),"changes":{h["applied"]["component"]:h["applied"]["correction"]},
                 "score":receipt["feedback"]["score"],"status":"succeeded","physical":cells,"equations":body(receipt["source"]),
                 "trace":[{"generator_plan":h["generator_plan"],"supervisor":h["applied"],"code_checks":h["checks"],
                           "result":result,"diff":h["diff"][:1600]}]})
        best=max(rows[-3:],key=lambda r:r["score"])
        save(work/"c-summary.json",{"control":mean(v[0] for v in control.values()),"completed":3,
             "best_new":best["round"],"score":best["score"],"rounds":[{"round":r["round"],"score":r["score"],
             "parent_round":r["parent_round"],"candidate_id":r["candidate_id"],"case_means":{
             c:mean(t["score"] for t in r["physical"] if t["case"]==c) for c in sorted({t["case"] for t in r["physical"]})}} for r in rows[-3:]]})
        return best["candidate_id"]
