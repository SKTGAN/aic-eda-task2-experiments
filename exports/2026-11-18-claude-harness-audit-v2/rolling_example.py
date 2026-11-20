"""Demonstrate reuse of measured controls and protection checks on the audit receipts."""

import json
from math import isfinite
from pathlib import Path
import subprocess
import sys


EVIDENCE = Path(__file__).resolve().parents[1]


def matching_removals(qualified_scores, anchor):
    """Find exact removal controls within one already verified comparison group."""
    if anchor not in qualified_scores or not isfinite(qualified_scores[anchor]):
        raise ValueError("The anchor needs a finite measured score")
    result = {}
    for factor in sorted(anchor):
        control = anchor - {factor}
        value = qualified_scores.get(control)
        result[factor] = {
            "control_factors": sorted(control),
            "status": "measured" if value is not None else "missing_control",
            "conditional_score_effect": qualified_scores[anchor] - value if value is not None else None,
        }
    return result


def cell_key(row):
    return row["case"], str(row["seed"])


def cell_index(receipt):
    cells = receipt["physical_cells"]
    result = {cell_key(row): row for row in cells}
    if len(cells) != receipt["expected_cells"] or len(result) != len(cells):
        raise ValueError("Incomplete or duplicate cells in the audit fixture")
    return result


def compare_cell(before, after):
    if any(r.get("status") != "succeeded" or r.get("valid") is not True for r in (before, after)):
        return {"status": "unmeasured_or_invalid"}
    values = {}
    for field in ("score", "wns_ns", "tns_ns"):
        a, b = before.get(field), after.get(field)
        if not all(isinstance(x, (int, float)) and isfinite(x) for x in (a, b)):
            values[field + "_delta"] = None
        else:
            values[field + "_delta"] = b - a
    return {"status": "measured", **values}


def main():
    check = EVIDENCE / "local-factorial" / "check_factorial.py"
    verified = json.loads(subprocess.check_output([sys.executable, "-B", str(check)], text=True))
    if not (verified["source_hashes_verified"] and verified["exact_loss_and_decoder_components_verified"]):
        raise ValueError("Unverified factorial example")
    measurements = verified["measurements"]
    arms = {"P": frozenset(), "A": frozenset("A"), "B": frozenset("B"), "AB": frozenset("AB")}
    scores = {arms[name]: row["common_reference_score"] for name, row in measurements.items()}
    removals = matching_removals(scores, arms["AB"])
    partial = {factors: score for factors, score in scores.items() if factors != arms["B"]}

    root = EVIDENCE / "runs" / "ours-new" / "rounds"
    anchor, child = [
        json.loads((root / ("round-%02d.json" % n)).read_text(encoding="utf-8")) for n in (3, 4)
    ]
    if child["submitted_search_decision"]["parent_id"] != anchor["request"]["candidate_id"]:
        raise ValueError("This child does not use the comparison anchor")
    before, after = cell_index(anchor), cell_index(child)
    if before.keys() != after.keys():
        raise ValueError("The two evaluation schedules differ")

    target = ("bp_fe-ng45", "1001")
    protected = [("ariane133-ng45", "1002"), ("ariane133-ng45", "1003")]
    weak_repair = {"case": target[0], "seed": target[1], **compare_cell(before[target], after[target])}
    preserved = [{"case": k[0], "seed": k[1], **compare_cell(before[k], after[k])} for k in protected]
    result = {
        "offline_audit_only": True,
        "measured_removals_from_AB": removals,
        "if_the_measured_B_receipt_had_been_missing": matching_removals(partial, arms["AB"]),
        "interaction_score_points": (
            verified["interaction_AB_minus_A_minus_B_plus_P"]["common_reference_score"]
        ),
        "nine_cell_observed_parent_vs_child": {
            "anchor_round": 3,
            "child_round": 4,
            "aggregate_score_delta": child["score"] - anchor["score"],
            "example_weak_target": weak_repair,
            "example_protected_cells": preserved,
            "protected_cells_were_designated_retrospectively_for_this_example": True,
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
