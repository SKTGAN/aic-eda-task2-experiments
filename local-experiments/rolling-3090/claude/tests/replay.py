"""Turn the archived official receipts into the summaries the Agent builds. Development material only.

The fixtures hold the bridge-visible cells, the organizer's per-cell partition diagnostics, the
accepted sources and each run's recorded lineage (tests/fixtures/three_servers.json), plus the
matched local A/B/AB receipts (tests/fixtures/local_factorial.json).
"""

import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
AGENT_DIR = Path(os.environ.get("AGENT_DIR") or HERE.parent / "next-harness" / "AgenticBench" / "agent" / "loss_decoder")
sys.path.insert(0, str(AGENT_DIR))

RUNS = json.loads((HERE / "fixtures" / "three_servers.json").read_text(encoding="utf-8"))
FACTORIAL = json.loads((HERE / "fixtures" / "local_factorial.json").read_text(encoding="utf-8"))

# official/reference/published_training_reference.json: reference deficits and published start timing.
PUBLISHED = {
    "ariane133-ng45": (0.5290353246723486, 96.42498143235612, {
        "1001": (-0.46473759489492794, -22.69812846368777),
        "1002": (-0.511323442504157, -101.00025635050363),
        "1003": (-0.5738236714876622, -29.767709140211068)}),
    "bp-ng45": (8.663351750761597, 6622.78575944895, {
        "1001": (-8.392474508445966, -9059.339646875793),
        "1002": (-7.841612026113778, -10349.946316496395),
        "1003": (-7.870566643414895, -8622.276498609612)}),
    "bp_fe-ng45": (0.9002498352590634, 716.9190029865956, {
        "1001": (-0.6611195111821111, -174.72074415142822),
        "1002": (-0.7280568576313236, -211.7487329856929),
        "1003": (-0.639466275808939, -188.35428327940795)}),
}
INITIAL = FACTORIAL["programs"]["P"]


def score(case, wns, tns):
    wns_ref, tns_ref, _ = PUBLISHED[case]
    wns_gain = (wns_ref - max(0.0, -wns)) / wns_ref
    tns_gain = (tns_ref - max(0.0, -tns)) / tns_ref
    return max(-100.0, 100 * (0.4 * wns_gain + 0.6 * tns_gain))


def schedule(rows):
    return [{"case": cell["case"], "seed": str(cell["seed"])} for cell in rows[0]["cells"]]


def official_score(cells):
    cases = []
    for cell in cells:
        if cell["case"] not in cases:
            cases.append(cell["case"])
    return sum(sum(c["score"] for c in cells if c["case"] == case) / sum(1 for c in cells if c["case"] == case)
               for case in cases) / len(cases)


def published_start(cells, candidate_id="official-initial"):
    rows = []
    for cell in cells:
        wns, tns = PUBLISHED[cell["case"]][2][cell["seed"]]
        rows.append({"case": cell["case"], "seed": cell["seed"], "status": "published_reference",
                     "score": score(cell["case"], wns, tns),
                     "metrics": {"final_global_wns_setup_ns": wns, "final_global_tns_setup_ns": tns}})
    return {"candidate_id": candidate_id, "status": "published_reference",
            "feedback": {"score": official_score(rows), "cells": rows}}


def summaries(rows, attempts=None):
    """The receipt summaries in evaluation order, with the organizer partition diagnostics attached."""
    result = []
    for row in rows:
        cells = []
        for cell in row["cells"]:
            key = "%s/%s" % (cell["case"], cell["seed"])
            summary = {k: cell[k] for k in ("case", "seed", "score", "valid", "status", "metrics") if k in cell}
            summary["seed"] = str(summary["seed"])
            if row.get("partition", {}).get(key):
                summary["partition_change_vs_initial"] = row["partition"][key]
            if cell.get("failure"):
                summary["failure"] = cell["failure"]
            cells.append(summary)
        attempt = dict(row.get("attempt") or {})
        attempt.update((attempts or {}).get(row["request_id"], {}))
        result.append({"request_id": row["request_id"], "candidate_id": row["candidate_id"],
                       "status": row["status"], "score": row["score"], "cells": cells, "attempt": attempt})
    return result


def sources(rows):
    return {row["request_id"]: row["source"] for row in rows}


def ledger_for(rows, attempts=None, fingerprints=None):
    import ledger
    views = summaries(rows, attempts)
    start = ledger.same_host_start(published_start(schedule(rows), rows[0]["attempt"]["parent_id"]), views)
    return ledger.build_ledger(views, sources(rows), schedule(rows), start, INITIAL, fingerprints)


def factorial_rows():
    """The local one-cell receipts as four complete official-looking evaluations of the same cell."""
    rows = []
    for name in ("P", "A", "B", "AB"):
        metrics = FACTORIAL["measurements"][name]
        cell = {"case": FACTORIAL["case"], "seed": str(FACTORIAL["seed"]), "status": "succeeded", "valid": True,
                "score": metrics["common_reference_score"], "metrics": {
                    "final_global_wns_setup_ns": metrics["final_global_wns_setup_ns"],
                    "final_global_tns_setup_ns": metrics["final_global_tns_setup_ns"],
                    "cut_net_count": metrics["cut_net_count"]}}
        # P is the official initial program, so its labels are the start labels (zero changed instances).
        partition = ({"%s/%s" % (cell["case"], cell["seed"]): {"partition_assignment_changed_count": 0}}
                     if name == "P" else {})
        rows.append({"request_id": "local-" + name, "candidate_id": "local-" + name, "status": "succeeded",
                     "score": cell["score"], "cells": [cell], "partition": partition,
                     "attempt": {"parent_id": "local-P" if name != "P" else "official-initial"},
                     "source": FACTORIAL["programs"][name]})
    return rows


BRANCHING = json.loads((HERE / "fixtures" / "branching_replay.json").read_text(encoding="utf-8"))
BRANCHING_RUNS = {"claude-original": "claude", "ours-new": "evidence"}


def baseline(run, rounds):
    """What the branching search control chose after `rounds` real receipts (its recorded replay)."""
    rows = RUNS[run]
    prefix = BRANCHING["runs"][BRANCHING_RUNS[run]]["prefixes"][rounds]
    if prefix["after_round"] != rounds:
        raise ValueError("Replay prefixes are out of order")
    parent = prefix["planner_parent"]
    parent_id = rows[0]["attempt"]["parent_id"] if parent == "initial" else rows[parent - 1]["candidate_id"]
    return parent_id, prefix["planner_intent"], dict(prefix["decision"])
