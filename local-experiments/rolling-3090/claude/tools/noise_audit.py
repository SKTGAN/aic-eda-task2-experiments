"""Separate repeatability from sensitivity in the archived receipts, and replay decisions under other
thresholds. Development material only; no model, bridge or evaluator is involved.

    python3 -I -B tools/noise_audit.py

Writes examples/noise_audit.json and examples/threshold_replay.json and prints a summary.

Repeatability: two measurements of the same labels. Within a run, two receipts whose organizer
diagnostic reports zero changed instances on a cell both carry the start labels there. Across runs,
the three runs ran on three different servers, so the same comparison is a cross-host repeat.
Sensitivity: two programs whose labels differ only a little on a cell (ledger.sensitivity_pairs).
The archive has no label files, so "a little" is bounded by each program's changed fraction against
the start (both at most LOCAL_FRACTION from the start grouping, same orientation); the exact distance
between the two programs is unknown.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import replay  # noqa: E402
import ledger as L  # noqa: E402
import rolling_plan as P  # noqa: E402

SERVERS = {"claude-original": "server A (port 15332)", "claude-new": "server B (port 27528)",
           "ours-new": "server C (port 10820)"}
DEFAULTS = {name: getattr(L, name) for name in ("SENSITIVITY_QUANTILE", "TOLERANCE_SCALE", "LOCAL_FRACTION",
                                                "ROOT_SEEDS", "DEFAULT_TOLERANCE", "MIN_TOLERANCE")}


def summary(values):
    if not values:
        return {"n": 0}
    return {"n": len(values), "min": round(min(values), 3), "q25": round(L.quantile(values, 0.25), 3),
            "median": round(L.quantile(values, 0.5), 3), "q75": round(L.quantile(values, 0.75), 3),
            "max": round(max(values), 3)}


def start_labelled_cells(run):
    """Cells whose organizer diagnostic reports zero changed instances: the start labels, measured."""
    rows = []
    for index, row in enumerate(replay.RUNS[run], 1):
        for cell in row["cells"]:
            key = "%s/%s" % (cell["case"], cell["seed"])
            if (row["partition"].get(key) or {}).get("partition_assignment_changed_count") == 0:
                metrics = cell.get("metrics") or {}
                rows.append({"run": run, "round": index, "cell": key, "score": cell["score"],
                             "wns": metrics.get("final_global_wns_setup_ns"), "tns": metrics.get("final_global_tns_setup_ns")})
    return rows


def repeatability():
    cells = [row for run in SERVERS for row in start_labelled_cells(run)]
    within, across = [], []
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            a, b = cells[i], cells[j]
            if a["cell"] != b["cell"]:
                continue
            same = all(x is not None and y is not None and abs(x - y) <= 1e-9
                       for x, y in ((a["score"], b["score"]), (a["wns"], b["wns"]), (a["tns"], b["tns"])))
            record = {"cell": a["cell"], "a": "%s R%d" % (a["run"], a["round"]), "b": "%s R%d" % (b["run"], b["round"]),
                      "identical_timing": same, "abs_score_delta": abs(a["score"] - b["score"])}
            (within if a["run"] == b["run"] else across).append(record)
    timing_twins = []
    for run in SERVERS:
        evidence = replay.ledger_for(replay.RUNS[run])
        for row in evidence["entries"][1:]:
            twin = L.duplicate_of(evidence, row["id"])
            if twin:
                timing_twins.append({"run": run, "entry": row["id"], **twin})
    return {"same_labels_within_a_server": within, "same_labels_across_servers": across,
            "whole_matrix_timing_twins_without_label_proof": timing_twins,
            "counts": {"within_pairs": len(within), "within_identical": sum(r["identical_timing"] for r in within),
                       "across_pairs": len(across), "across_identical": sum(r["identical_timing"] for r in across)}}


def sensitivity(run, rounds=None):
    rows = replay.RUNS[run][:rounds] if rounds else replay.RUNS[run]
    evidence = replay.ledger_for(rows)
    pairs = L.sensitivity_pairs(evidence)
    tol = L.tolerances(evidence)
    cases = {}
    for case in evidence["cases"]:
        values = [row["abs_delta"] for row in pairs if row["case"] == case]
        cases[case] = {"abs_score_change": summary(values), "tolerance": tol[case],
                       "distinct_programs": len({p for row in pairs if row["case"] == case for p in (row["a"], row["b"])})}
    seeds = {case: sum(1 for key in evidence["schedule"] if key[0] == case) for case in evidence["cases"]}
    derivation = {
        "cell_sensitivity": {case: tol[case]["cell"] for case in tol},
        "case_mean_tolerance": {case: "max(%.1f, %.3f / sqrt(%d)) = %.3f" % (
            L.MIN_TOLERANCE, tol[case]["cell"], seeds[case], tol[case]["case_mean"]) for case in tol},
        "aggregate": "sqrt(%s) / %d = %.3f" % (" + ".join("%.3f^2" % tol[case]["case_mean"] for case in tol),
                                               len(tol), L.aggregate_tolerance(evidence, tol)),
    }
    return {"run": run, "rounds": len(rows), "cases": cases, "derivation": derivation,
            "raw_pairs": [{**row, "abs_delta": round(row["abs_delta"], 4),
                           "scores": [round(v, 4) for v in row["scores"]],
                           "moved_vs_start": [None if v is None else round(v, 5) for v in row["moved_vs_start"]]}
                          for row in pairs]}


SETTINGS = [
    ("default (median, x1, local 0.10, /sqrt(seeds))", {}),
    ("25th percentile", {"SENSITIVITY_QUANTILE": 0.25}),
    ("75th percentile", {"SENSITIVITY_QUANTILE": 0.75}),
    ("half the median", {"TOLERANCE_SCALE": 0.5}),
    ("twice the median", {"TOLERANCE_SCALE": 2.0}),
    ("local pairs within 0.05", {"LOCAL_FRACTION": 0.05}),
    ("local pairs within 0.20", {"LOCAL_FRACTION": 0.20}),
    ("no sqrt(seeds) division", {"ROOT_SEEDS": False}),
    ("default tolerance 2", {"DEFAULT_TOLERANCE": 2.0}),
    ("default tolerance 10", {"DEFAULT_TOLERANCE": 10.0}),
    ("zero tolerance (every decrease counts)", {"TOLERANCE_SCALE": 0.0, "MIN_TOLERANCE": 0.0, "DEFAULT_TOLERANCE": 0.0}),
]


def considered(rows):
    return {(f["loss"], f["decoder"]) for f in (L.factor_ids(row["source"]) for row in rows)}


def decisions(run, rounds_list):
    out = {}
    for rounds in rounds_list:
        rows = replay.RUNS[run][:rounds]
        evidence = replay.ledger_for(rows)
        plan = P.plan_next(evidence, replay.baseline(run, rounds), 10 - rounds, 10, considered(rows))
        choice = plan["choice"]
        gain = plan["baseline"]["reason"] == "targeted_repair" and replay.baseline(run, rounds)[2]["protect_gain"]
        out["after R%d" % rounds] = {
            "branching": "%s %s %s" % (plan["baseline"]["reason"], plan["baseline"]["parent"], plan["baseline"]["intent"]),
            "rolling": "%s %s %s" % (choice["kind"], choice["parent"], choice["component"]),
            "changed": (choice["kind"] != "edit" or plan["decision_override"] is not None),
            "planning_call": plan["hard"],
            "protected_gain_vs_cell_tolerance": None if not gain else "%+.2f vs %.2f (%s)" % (
                gain["score_delta"], plan["tolerances"][gain["case"]]["cell"], gain["case"]),
        }
    return out


def threshold_replay():
    table = []
    for label, changes in SETTINGS:
        for name, value in DEFAULTS.items():
            setattr(L, name, value)
        for name, value in changes.items():
            setattr(L, name, value)
        table.append({"setting": label, "parameters": changes,
                      "claude-original": decisions("claude-original", range(1, 11)),
                      "ours-new": decisions("ours-new", range(1, 5))})
    for name, value in DEFAULTS.items():
        setattr(L, name, value)
    return table


def main():
    audit = {"repeatability": repeatability(),
             "sensitivity": [sensitivity("claude-original"), sensitivity("claude-original", 4),
                             sensitivity("claude-original", 7), sensitivity("claude-original", 9),
                             sensitivity("ours-new"), sensitivity("ours-new", 3), sensitivity("claude-new")]}
    replayed = threshold_replay()
    out = ROOT / "examples"
    out.mkdir(exist_ok=True)
    (out / "noise_audit.json").write_text(json.dumps(audit, indent=1) + "\n", encoding="utf-8")
    (out / "threshold_replay.json").write_text(json.dumps(replayed, indent=1) + "\n", encoding="utf-8")
    counts = audit["repeatability"]["counts"]
    print("matched repeats:", counts)
    for row in audit["sensitivity"]:
        print("sensitivity %s R1-R%d:" % (row["run"], row["rounds"]),
              {case: (value["abs_score_change"].get("n"), value["abs_score_change"].get("median"), value["tolerance"]["source"])
               for case, value in row["cases"].items()}, row["derivation"]["aggregate"])
    for setting in replayed:
        flags = [(key, value["rolling"], ",".join(value["planning_call"]) or "-")
                 for key, value in setting["claude-original"].items() if value["changed"] or key in ("after R4", "after R7", "after R9")]
        print("%-42s" % setting["setting"], flags)


if __name__ == "__main__":
    main()
