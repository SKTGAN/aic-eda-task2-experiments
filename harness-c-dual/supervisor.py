"""Evidence preparation and the contract between the C generator and reviewer."""
import ast
import difflib
import json
from statistics import mean

DOMAIN = """Development references: TP-GNN couples learned embeddings to area-weighted clustering.
Final 3D timing follows feasible tier assignment and placement. Inspect raw, balanced and feasible cuts,
repair area and final WNS/TNS together. Area balance and lower cut count alone do not establish a timing gain.
Whole-die exchange preserves grouping but may change physical timing. Distinguish these from moved groups.
Claude34's R2 loss earned 29.43; its R4 decoder child earned 34.75, almost all the marginal gain on
one die exchange. R6 repeated R4's full matrix. In the separate 4060 development trajectory the
33.91 -> 34.39 -> 39.68 -> 41.73 decoder sequence protected previously good cells while testing changes
on a weak case; the final bp_fe gains were mixed across seeds and the six other results held.
These are development observations, not scores on layout C. Never condition executable code on case
names, seeds as identities, benchmark sizes or memorized labels. Compare legal numerical rules that
can generalize. Use real receipts to decide whether an observed tradeoff was resolved."""

PLANNER = """Act as the C candidate generator. Read the past attempts, exact executable parent mechanisms,
previous public dialogue and calibrated physical results. Propose one feasible single-component change.
Return only JSON {parent_round:int,component:"loss" or "decoder",protect_cell:string,target_cell:string,
hypothesis:string,prediction:string,falsifier:string}. The two cells are case/seed keys for evaluation,
not conditions in code. Prefer a parent with measured performance on layout C; motivate any alternative.
The control is the unchanged historical R4 on this layout. Account for the outcome of the most recent trial."""
AUDITOR = """You supervise the generator, independently of its search. Examine prior visible proposals,
actual edits, repair-chain measurements, conflicting seed outcomes and the current proposal. Identify
one specific recurring error or a justified decision to keep the proposal. Compare candidate R2->R4->R6
and the 41-point development process where relevant. Select one reversible intervention in parent,
scope or hypothesis. Give a concrete non-case-specific implementation direction and a measurable test.
Return only JSON {parent_round:int,component:"loss" or "decoder",evidence:[{round:int,cell:string},...],
correction:string,protect_cell:string,target_cell:string,prediction:string,falsifier:string}.
Cite at least two actual rounds; cite the latest measured round among them. Respect actual input/compute
interfaces and the fixed C layout. Do not presume that historical scores reproduce on this layout."""
CHECK = """Independently review the candidate actually written. Compare its executable diff with your previous
correction and the parent's mechanism. Verify promised scope and protection, distinguish a proxy from physical
evidence. Testing success will only be known after the matrix. If the claimed operation is missing or a known
failed edit is being repeated, request one concrete correction. Return JSON {verdict:"accept" or "revise",
finding:string,required_change:string}. Evaluate the code body rather than comments. No code in the response."""
METRICS=("tp_gnn_raw_cut_net_count","tp_gnn_balanced_cut_net_count","tp_gnn_feasible_cut_net_count",
         "tp_gnn_repair_moved_area_fraction","timing_weighted_cut","partition_assignment_changed_count")

def packed_cells(cells):
    return {c["case"]+"/"+str(c["seed"]):[c.get("score"),(c.get("metrics") or {}).get("final_global_wns_setup_ns"),
        (c.get("metrics") or {}).get("final_global_tns_setup_ns")]+[(c.get("metrics") or {}).get(k) for k in METRICS]
        for c in cells}

def rounded(v):return round(v,4) if isinstance(v,(int,float)) else None

def packet(rows,control):
    order=sorted(control)
    res=[]
    for row in rows:
        obs=packed_cells(row["physical"])
        trace=row["trace"]
        if row["round"]<=10:
            trace=[t for t in trace if t.get("visible_reply") or t.get("reason") or t.get("retry")][-3:]
        funcs=row["equations"]
        keys=list(row.get("changes",{}))
        component="decode_tp_gnn_embeddings" if keys==["decoder"] else "compute_tp_gnn_loss"
        res.append({"round":row["round"],"host":row["host"],"parent":row.get("parent_round"),
                    "score":rounded(row["score"]),"changed":keys,"actual_function":funcs.get(component,"")[:2000],
                    "cells":[[rounded(x) for x in obs[k]] for k in order],"dialogue":trace})
        if row["round"] == 4:
            res[-1].update(host="C", score=rounded(mean(v[0] for v in control.values())),
                           cells=[[rounded(x) for x in control[k]] for k in order],
                           archived_other_host={"host":row["host"],"score":rounded(row["score"]),
                                                "cells":[[rounded(x) for x in obs[k]] for k in order]},
                           dialogue_origin="historical host; judge the repeat using the C cells")
    return {"layout":"C: 26016 dual 3080 + 22120 3090; fixed cell routing","cell_order":order,
            "same_layout_mean_by_parent":{str(r["round"]):r["score"] for r in res if r["host"]=="C"},
            "columns":["score","WNS_ns","TNS_ns",*METRICS],"same_layout_parent_R4_control":
            [[rounded(v) for v in control[k]] for k in order],"rounds":res}

def obj(text):
    t=text.strip()
    if t.startswith("```") and t.endswith("```"):t="\n".join(t.splitlines()[1:-1])
    v=json.loads(t)
    if not isinstance(v,dict):raise ValueError("Expected a JSON object")
    return v

def check_plan(p, rows, cells, supervision=False):
    ids={r["round"] for r in rows if r.get("status")=="succeeded"}
    if type(p.get("parent_round")) is not int or p["parent_round"] not in ids:
        raise ValueError("parent_round must identify an observed successful trial")
    if p.get("component") not in ("loss","decoder"):raise ValueError("Unknown component")
    parent = next(r for r in rows if r["round"] == p["parent_round"])
    local_score = mean(v[0] for v in cells.values()) if parent["round"] == 4 else (
        parent["score"] if parent["host"] == "C" else None)
    stated = p.get("parent_mean_on_C")
    if "parent_mean_on_C" not in p or (local_score is None and stated is not None) or (
            local_score is not None and (type(stated) not in (int,float) or abs(stated-local_score)>0.011)):
        raise ValueError("Use parent_mean_on_C from same_layout_mean_by_parent, null if absent: "
                         + str(rounded(local_score)))
    for key in ("protect_cell","target_cell"):
        if p.get(key) not in cells:raise ValueError("Use exact case/seed keys for "+key)
    for key in (("correction",) if supervision else ("hypothesis",))+("prediction","falsifier"):
        if not isinstance(p.get(key),str) or not p[key].strip():raise ValueError("Missing "+key)
    if supervision:
        ref=p.get("evidence")
        if not isinstance(ref,list) or not 2<=len(ref)<=6:raise ValueError("Cite two to six observations")
        for e in ref:
            if not isinstance(e,dict) or type(e.get("round")) is not int or e["round"] not in ids or e.get("cell") not in cells:
                raise ValueError("Invalid round/cell evidence")
        cited={e["round"] for e in ref}
        if len(cited)<2 or rows[-1]["round"] not in cited:raise ValueError("Include different rounds and the latest round")
    return p

def body(source):
    funcs={}
    for f in ast.parse(source).body:
        if isinstance(f,ast.FunctionDef):
            funcs[f.name]="\n".join(ast.unparse(s) for s in f.body if not isinstance(s,ast.Expr))
    return funcs

def change(before,after):
    a=body(before); b=body(after)
    return "\n".join(difflib.unified_diff(("\n".join(a.values())).splitlines(),("\n".join(b.values())).splitlines(),
                                            fromfile="parent",tofile="candidate",lineterm=""))
