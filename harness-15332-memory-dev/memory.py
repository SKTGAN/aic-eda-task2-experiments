"""Summarize observed experiments for both the planner and the editor."""

import json
from statistics import mean


def measured_row(number, host, candidate, parent, score, cells, changes, status):
    measurements = {}
    for cell in cells:
        key = "{}/{}".format(cell["case"], cell["seed"])
        if key in measurements:
            raise ValueError("Duplicate case/seed " + key)
        m = cell.get("metrics") or {}
        measurements[key] = [cell.get("score"), m.get("final_global_wns_setup_ns"),
                             m.get("final_global_tns_setup_ns"), m.get("partition_assignment_changed_count")]
    return dict(round=number, host=host, candidate_id=candidate, parent_id=parent, score=score,
                changes=changes, status=status, cells=measurements)


def rounded(value):
    return round(value, 3) if isinstance(value, (int, float)) else None


def describe(rows):
    by_id = {r["candidate_id"]: r for r in rows}
    order = sorted(set(k for row in rows for k in row["cells"]))
    trials = []
    for r in rows:
        parent = by_id.get(r["parent_id"])
        cells = r["cells"]
        summary = {
            "round": r["round"], "host": r["host"], "parent": parent["round"] if parent else "published start",
            "status": r["status"], "score": rounded(r["score"]),
            "changes": {k: " ".join(str(v).split())[:420] for k,v in r["changes"].items()},
            "observations": [[rounded(x) for x in cells[k]] if k in cells else None for k in order],
        }
        if parent:
            summary["paired_host"] = "same" if parent["host"] == r["host"] else "different"
            ds = {k: cells[k][0] - parent["cells"][k][0] for k in cells.keys() & parent["cells"].keys()
                  if cells[k][0] is not None and parent["cells"][k][0] is not None}
            if ds:
                summary["mean_delta_by_case"] = {case: rounded(mean(v for k,v in ds.items() if k.rsplit("/",1)[0] == case))
                    for case in sorted({k.rsplit("/",1)[0] for k in ds})}
                worst = min(ds,key=lambda k:(ds[k],k))
                summary["worst_paired_cell"] = [worst,rounded(ds[worst])]
        trials.append(summary)
    return {"cell_order":order, "observation_columns":["score","WNS_ns","TNS_ns","labels_changed_vs_start"],
            "rounds":trials}


def read_plan(text, rows):
    body=text.strip()
    if body.startswith("```") and body.endswith("```"):
        body="\n".join(body.splitlines()[1:-1])
    plan=json.loads(body)
    if not isinstance(plan,dict):
        raise ValueError("Return a JSON object")
    by_n={r["round"]: r for r in rows}
    parent=plan.get("parent_round")
    if type(parent) is not int or parent not in by_n or by_n[parent]["status"]!="succeeded":
        raise ValueError("Select an observed, successful parent_round")
    if plan.get("component") not in ("loss","decoder"):
        raise ValueError("Select loss or decoder")
    evidence=plan.get("evidence")
    if not isinstance(evidence,list) or not 2<=len(evidence)<=5:
        raise ValueError("Cite two to five historical observations")
    cited=set()
    for item in evidence:
        if not isinstance(item,dict):
            raise ValueError("Each citation must be a round and cell")
        n,key=item.get("round"),item.get("cell")
        if type(n) is not int or n not in by_n or not isinstance(key,str) or key not in by_n[n]["cells"]:
            raise ValueError("A citation does not match any observed round/cell")
        cited.add(n)
    if len(cited)<2 or not isinstance(plan.get("experiment"),str) or not plan["experiment"].strip():
        raise ValueError("Cite different rounds and give an experiment")
    if rows[-1]["host"]=="26016" and rows[-1]["round"] not in cited:
        raise ValueError("Use the latest 26016 result in the decision")
    return plan
