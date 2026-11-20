"""Align this run's receipts on design and seed before either model call."""
from difflib import unified_diff


TIMING = {"wns_ns": "final_global_wns_setup_ns", "tns_ns": "final_global_tns_setup_ns"}
PHYSICAL = {
    "raw_cut": "tp_gnn_raw_cut_net_count", "balanced_cut": "tp_gnn_balanced_cut_net_count",
    "feasible_cut": "tp_gnn_feasible_cut_net_count", "repair_moves": "tp_gnn_repair_moved_supernodes",
    "repair_area_fraction": "tp_gnn_repair_moved_area_fraction", "final_cut": "cut_net_count",
    "weighted_cut": "timing_weighted_cut", "area_error": "area_balance_error",
    "macro_count_error": "macro_count_error", "macro_area_error": "macro_area_error",
    "final_loss": "tp_gnn_final_loss",
}
CORE = ("case", "seed", "status", "valid", "score", "wns_ns", "tns_ns")
PAIRED = ("delta_score_parent", "delta_wns_ns_parent", "delta_tns_ns_parent")


def index(cells):
    return {(c["case"], str(c["seed"])): c for c in cells}


def table(rows, required):
    # Keep a single header per trial. Drop only optional columns absent in every seed.
    columns = list(required)
    for row in rows:
        for key, value in row.items():
            if value is not None and key not in columns:
                columns.append(key)
    return {"columns": columns, "rows": [
        [round(row[k], 7) if isinstance(row.get(k), float) else row.get(k) for k in columns] for row in rows]}


def values(cell):
    metrics = cell.get("metrics") or {}
    return {"score": cell.get("score"), **{name: metrics.get(key) for name, key in TIMING.items()}}


def measured(cell):
    return cell.get("status") in ("succeeded", "published_reference") and cell.get("valid") is not False


def delta_to(cell, other, reference):
    if not measured(cell) or not measured(other):
        return {}
    before = values(other)
    return {"delta_" + name + "_" + reference: value - before[name] for name, value in values(cell).items()
            if isinstance(value, (float, int)) and isinstance(before[name], (float, int))}


def seed_row(key, cell, parent, baseline, pair):
    metrics = cell.get("metrics") or {}
    moved = cell.get("partition_change_vs_initial") or {}
    assignments = pair.get("assignment_vs_parent") or {}
    row = {"case": key[0], "seed": key[1], "status": cell.get("status", "unreported" if cell else "missing"),
           "valid": cell.get("valid"), **values(cell), **delta_to(cell, parent, "parent"),
           **delta_to(cell, baseline, "start")}
    # The paired receipt can establish a score delta even when its parent source is unavailable.
    if measured(cell) and (not parent or measured(parent)):
        if pair.get("score_delta") is not None:
            row["delta_score_parent"] = pair["score_delta"]
        for timing, weight in (("wns", 40), ("tns", 60)):
            value = pair.get(timing + "_deficit_improvement_delta")
            if value is not None:
                row[timing + "_points_parent_before_floor"] = weight * value
    row.update({label: metrics.get(field) for label, field in PHYSICAL.items()})
    if row["repair_area_fraction"] is None:
        row["repair_area_fraction"] = moved.get("tp_gnn_repair_moved_area_fraction")
    row.update({"changed_from_initial": moved.get("partition_assignment_changed_count"),
                "fraction_from_initial_up_to_swap": moved.get("moved_fraction_up_to_swap"),
                "changed_from_parent": assignments.get("changed_count"),
                "fraction_from_parent_up_to_swap": assignments.get("moved_fraction_up_to_swap"),
                "top_to_bottom_from_parent": assignments.get("top_to_bottom"),
                "bottom_to_top_from_parent": assignments.get("bottom_to_top"),
                "failure": cell.get("failure") or cell.get("reason")})
    return row


def experiment_record(initial, parent_source, parent_id, start, archive, schedule, probes):
    keys = [(item["case"], str(item["seed"])) for item in schedule]
    base = index(((start or {}).get("feedback") or {}).get("cells", []))
    origins = []
    for key in keys:
        cell = base.get(key, {})
        origins.append({"case": key[0], "seed": key[1], "status": cell.get("status", "missing"),
                        **values(cell), "origin": cell.get("measured_on", "published") if cell else None})
    by_candidate = {start["candidate_id"]: base} if start else {}
    history = []
    for trial in archive:
        attempt = trial.get("attempt") or {}
        comp = trial.get("parent_comparison") or {}
        parent = attempt.get("parent_id") or comp.get("parent_id")
        before = by_candidate.get(parent, {})
        cells = index(trial["cells"])
        pairs = index(comp.get("cells", [])) if comp.get("parent_id") in (None, parent) else {}
        rows = [seed_row(key, cells.get(key, {}), before.get(key, {}), base.get(key, {}), pairs.get(key, {}))
                for key in keys]
        history.append({"id": trial["candidate_id"], "parent": parent, "parent_reference_kind": comp.get("parent_source"),
                        "change": attempt.get("changed_components"), "plan_at_submission": attempt.get("plan"),
                        "score": trial.get("score"), "delta_to_parent": comp.get("official_score_delta"),
                        "case_means": {k: round(v["mean"], 7) for k, v in trial["case_scores"].items()},
                        "seed_results": table(rows, CORE + PAIRED), "biggest_regression": comp.get("largest_regression"),
                        "status": trial["status"], "issue": trial.get("reason") or trial.get("analysis_error"),
                        "donor": attempt.get("component_donor")})
        if trial["status"] == "succeeded":
            by_candidate[trial["candidate_id"]] = cells
    diff = "\n".join(unified_diff(initial.splitlines(), parent_source.splitlines(), n=1, lineterm=""))
    return {"official_initial_program": initial if initial != parent_source else {"same_as": "parent_program"},
            "selected_parent": parent_id, "diff_from_initial": diff[:2400], "diff_truncated": len(diff) > 2400,
            "start_measurements": table(origins, ("case", "seed", "status", "score", "wns_ns", "tns_ns", "origin")),
            "history": history, "synthetic_probes": probes,
            "readout": "Each trial's seed_results lists every scheduled case and seed. Raw timing deltas are child minus "
                       "its own matched parent or start. WNS/TNS point contributions precede the cell score floor. "
                       "Null or absent optional metrics mean unobserved. CPU synthetic seeds have no STA timing."}

