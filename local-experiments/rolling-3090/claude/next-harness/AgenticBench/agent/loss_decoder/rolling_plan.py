"""Decide the next experiment after every completed evaluation, from this run's evidence ledger.

The branching search control still proposes a parent and the one function to edit. This module
states what that experiment is for before any code is generated: the weak target, the gains to
protect with their tolerances, and the outcome that would contradict the plan. It may replace the
model edit with a deterministic splice of measured functions (a removal, transplant or merge) when
that answers a question the next decision depends on. It never assigns a score; the final choice
stays with the official complete training matrix.

Standard library only (Python 3.8). Case and seed labels are evidence labels, never program rules.
"""

import ast
import json
import re

import ledger as L


SPLICES = ("removal", "transplant", "merge")
# Baseline decisions this module never overrides: openings, failures and contract repairs.
KEEP_BASELINE = ("opening_control", "complementary_opening_with_first_receipt", "no_complete_candidate",
                 "execution_evidence_unusable", "replace_invalid_component")
CONTRADICTED = ("target_met_protection_failed", "target_missed_protection_failed", "target_missed_protection_held")
MAX_PLANNING_CALLS = 4
# When true, a decision that departs from the branching choice (a removal, transplant, merge,
# declined repair or removal follow-up) also asks the high-effort planner, offering the branching
# choice as an alternative. Off by default: on the archived prefixes these departures rest on
# measured ledger facts, and the value of a second opinion there is unmeasured (see the live plan).
PLAN_ON_OVERRIDE = False
CONFOUNDING = ("orientation", "published_reference", "timing_changed_same_labels")


def _cell(row):
    return "%s/%s" % (row["case"], row["seed"])


def other(component):
    return "decoder" if component == "loss" else "loss"


# ----------------------------------------------------------------------------------------------
# What the anchor has, what it lacks


def review_anchor(ledger, label, tol):
    """The anchor against the start: weak case, protected gains, fragile gains and confounders."""
    result = L.contrast(ledger, label, "S", tol)
    anchor = L.entry(ledger, label)
    start = ledger["entries"][0]
    protected, fragile = [], []
    for case_row in result["cases"]:
        cells = [row for row in result["cells"] if row["case"] == case_row["case"]]
        supported = L.case_supported(case_row)
        # A design whose measured scores are well above the start on most seeds is kept even when the
        # start value of some seed is only published; the evidence label records the weaker footing.
        mixed = (not supported and case_row["mean_delta"] is not None
                 and case_row["mean_delta"] >= case_row["tolerance"] and case_row["improved"] * 2 > case_row["seeds"])
        if supported or mixed:
            protected.append({
                "case": case_row["case"], "mean_delta": case_row["mean_delta"], "tolerance": case_row["tolerance"],
                "cell_tolerance": tol[case_row["case"]]["cell"],
                "seeds": [row["seed"] for row in cells if row["delta"] is not None and row["delta"] > L.SCORE_EPS],
                "strength": "supported" if supported else "mixed_reference", "evidence": result["id"]})
        for row in cells if not (supported or mixed) else ():
            # A gain outside the protected designs that rests on an exchange, a published start value
            # or a timing change with identical labels: reported, not protected.
            if row["delta"] is not None and row["delta"] > L.SCORE_EPS and row["strength"] in CONFOUNDING:
                fragile.append({"cell": _cell(row), "delta": row["delta"], "reason": row["strength"]})
    protected_cases = {row["case"] for row in protected}
    def case_mean(case):
        scores = [anchor["cells"][key]["score"] for key in ledger["schedule"] if key[0] == case]
        return sum(scores) / len(scores) if all(value is not None for value in scores) else None
    open_cases = [row for row in result["cases"] if row["case"] not in protected_cases] or result["cases"]
    weak_row = min(open_cases, key=lambda row: (row["mean_delta"] if row["mean_delta"] is not None else 1e9,
                                                case_mean(row["case"]) or 0.0))
    weak = {"case": weak_row["case"], "mean_delta": weak_row["mean_delta"], "anchor_case_mean": case_mean(weak_row["case"]),
            "seeds": [row["seed"] for row in result["cells"] if row["case"] == weak_row["case"]],
            "cells": [{"seed": row["seed"], "delta": row["delta"], "evidence": row["strength"]}
                      for row in result["cells"] if row["case"] == weak_row["case"]]}
    confounders = [{"cell": _cell(row), "issue": row["strength"]} for row in result["cells"]
                   if row.get("strength") in CONFOUNDING]
    rows = [{"cell": _cell(row), "anchor": anchor["cells"][(row["case"], row["seed"])]["score"],
             "start": start["cells"][(row["case"], row["seed"])]["score"],
             "start_measured_on": start["cells"][(row["case"], row["seed"])].get("measured_on"),
             "delta": row["delta"], "wns_delta_ns": row.get("wns_delta_ns"), "tns_delta_ns": row.get("tns_delta_ns"),
             "labels_vs_start": row.get("relation"), "evidence": row["strength"]} for row in result["cells"]]
    return {"anchor": label, "versus": "S", "official_delta": result["official_delta"], "reading": L.gain_reading(result),
            "weak": weak, "protected": protected, "fragile": fragile, "confounders": confounders, "rows": rows}


def retarget(review, case, keep, tol):
    """The same review with an externally named target design (and, optionally, one more to keep)."""
    rows = [row for row in review["rows"] if row["cell"].split("/")[0] == case]
    deltas = [row["delta"] for row in rows]
    weak = {"case": case, "seeds": [row["cell"].split("/")[1] for row in rows],
            "mean_delta": sum(deltas) / len(deltas) if rows and None not in deltas else None,
            "anchor_case_mean": None, "cells": [{"seed": row["cell"].split("/")[1], "delta": row["delta"],
                                                 "evidence": row["evidence"]} for row in rows]}
    protected = [row for row in review["protected"] if row["case"] != case]
    if keep and keep != case and keep not in [row["case"] for row in protected]:
        protected.append({"case": keep, "mean_delta": None, "seeds": [], "tolerance": tol[keep]["case_mean"],
                          "cell_tolerance": tol[keep]["cell"], "strength": "named_by_repair",
                          "evidence": "decision.protect_gain"})
    return dict(review, weak=weak, protected=protected)


MEASUREMENTS = ("removal", "merge")  # experiments that answer a question rather than repair a design


def make_contract(review, component, tol, anchor_candidate=None, kind="edit"):
    """Success and protection criteria for the next experiment, fixed before it is generated.

    A removal or a merge is a measurement: it has no target design, and its decision table, not a
    protection rule, says what happens next. Edits and transplants carry a target and protections.
    """
    weak = review["weak"]
    measured = kind in MEASUREMENTS
    protected = [row for row in review["protected"] if row["case"] != weak["case"]]
    for case, bound in tol.items():
        if case != weak["case"] and not any(row["case"] == case for row in protected):
            anchors = [row.get("anchor") for row in review.get("rows", []) if row["cell"].split("/")[0] == case]
            if anchors and all(score is not None for score in anchors):
                protected.append({"case": case, "tolerance": bound["case_mean"], "cell_tolerance": bound["cell"],
                                  "strength": "parent_floor", "evidence": review["anchor"]})
    return {
        "anchor": review["anchor"], "anchor_candidate": anchor_candidate, "component": component, "kind": kind,
        "target": None if measured else {
            "case": weak["case"], "seeds": weak["seeds"],
            "rule": "mean paired score delta over the case > 0 and most of its seeds improve"},
        "protect": [] if measured else [
            {"case": row["case"], "tolerance": row["tolerance"], "cell_tolerance": row["cell_tolerance"],
             "strength": row["strength"], "evidence": row["evidence"],
             "rule": "mean paired score delta over the case >= -tolerance"}
            for row in protected],
        "fragile": [row["cell"] for row in review["fragile"]],
        # Fixed with the plan: the verdict never uses a tolerance recalibrated on its own result.
        "tolerances": {case: {key: tol[case][key] for key in ("cell", "case_mean", "pairs", "source")} for case in tol},
    }


def _label(ledger, label, candidate=None):
    """A ledger label, resolved by candidate id when one was stored (labels follow evaluation order)."""
    row = ledger["by_candidate"].get(candidate) if candidate else None
    return row["id"] if row else label


def judge(ledger, contract, child, tol=None):
    """Compare a measured child with its declared contract (tolerances as stored at plan time)."""
    anchor = _label(ledger, contract["anchor"], contract.get("anchor_candidate"))
    result = L.contrast(ledger, child, anchor, contract.get("tolerances") or tol)
    verdict = {"child": child, "anchor": anchor, "official_delta": result["official_delta"],
               "reading": L.gain_reading(result), "evidence": result["id"]}
    if not result["complete"]:
        verdict["verdict"] = "incomplete"
        return verdict
    if any(row.get("strength") == "runtime_environment" for row in result["cells"]):
        verdict["verdict"] = "environment_confounded"
        return verdict
    if result["inert_cells"] * 2 > len(result["cells"]):
        verdict["verdict"] = "inert"
        return verdict
    if contract.get("target") is None:
        verdict["verdict"] = "measured"  # a removal or merge: its decision table decides what follows
        return verdict
    cases = {row["case"]: row for row in result["cases"]}
    target = cases[contract["target"]["case"]]
    met = target["mean_delta"] is not None and target["mean_delta"] > L.SCORE_EPS and target["improved"] * 2 > target["seeds"]
    verdict["target"] = {"case": target["case"], "mean_delta": target["mean_delta"], "improved_seeds": target["improved"],
                         "seeds": target["seeds"], "met": met,
                         "cells": [{"cell": _cell(row), "delta": row["delta"], "evidence": row["strength"]}
                                   for row in result["cells"] if row["case"] == target["case"]]}
    protection, regressions = [], []
    for rule in contract["protect"]:
        row = cases[rule["case"]]
        held = row["mean_delta"] is not None and row["mean_delta"] >= -rule["tolerance"]
        protection.append({"case": rule["case"], "mean_delta": row["mean_delta"], "tolerance": rule["tolerance"],
                           "held": held})
        for cell in result["cells"]:
            if cell["case"] == rule["case"] and cell["delta"] is not None and cell["delta"] < -L.SCORE_EPS:
                regressions.append({"cell": _cell(cell), "delta": cell["delta"], "evidence": cell["strength"],
                                    "beyond_cell_tolerance": cell["delta"] < -rule["cell_tolerance"]})
    verdict["protect"] = protection
    verdict["protected_regressions"] = sorted(regressions, key=lambda row: row["delta"])
    verdict["verdict"] = ("target_met" if met else "target_missed") + (
        "_protection_held" if all(row["held"] for row in protection) else "_protection_failed")
    return verdict


# ----------------------------------------------------------------------------------------------
# Candidate experiments


def _spliced(ledger, factors, considered):
    key = (factors["loss"], factors["decoder"])
    return L.find_program(ledger, factors) is None and key not in considered


def _source_for(ledger, factors):
    """For each component, the entry whose measured program supplies that exact function."""
    donors = {}
    for component in L.COMPONENTS:
        donor = next((row for row in ledger["entries"] if row["factors"]
                      and row["factors"][component] == factors[component]), None)
        if donor is None:
            return None
        donors[component] = donor["id"]
    return donors


def merge_options(ledger, tol, considered):
    """Two credited single-function gains over one common measured base, not yet combined."""
    options = []
    complete = [row for row in ledger["entries"] if row["complete"] and row["factors"]]
    for base in complete:
        singles = {}
        for row in complete:
            differs = [c for c in L.COMPONENTS if row["factors"][c] != base["factors"][c]]
            if len(differs) == 1:
                result = L.contrast(ledger, row["id"], base["id"], tol)
                if L.credited_gain(result):
                    singles.setdefault(differs[0], []).append((row, result))
        for x, x_result in singles.get("loss", []):
            for y, y_result in singles.get("decoder", []):
                factors = {"loss": x["factors"]["loss"], "decoder": y["factors"]["decoder"]}
                if not _spliced(ledger, factors, considered):
                    continue
                parent, donor = (x, y) if x["score"] >= y["score"] else (y, x)
                component = "decoder" if parent is x else "loss"
                options.append({
                    "kind": "merge", "parent": parent["id"], "component": component, "factors": factors,
                    "donors": _source_for(ledger, factors), "evidence": [x_result["id"], y_result["id"]],
                    "value": x_result["official_delta"] + y_result["official_delta"],
                    "question": "Do the loss gain of %s and the decoder gain of %s over %s add up?" % (
                        x["id"], y["id"], base["id"]),
                    "decides": {"if_above_both": "the merge becomes the anchor",
                                "if_below_either": "keep the stronger single change and record the interaction"},
                    "hypotheses": ["the loss gain of %s (%+.2f) and the decoder gain of %s (%+.2f) are separate "
                                   "mechanisms and add" % (x["id"], x_result["official_delta"], y["id"],
                                                           y_result["official_delta"]),
                                   "the two gains act on the same boundary groups, so combining them interferes"],
                    "falsifier": "the merge scores below the stronger of %s and %s" % (x["id"], y["id"])})
    return sorted(options, key=lambda row: -row["value"])


def transplant_options(ledger, anchor, weak_case, tol, considered):
    """A function that gave the anchor's weak design a supported gain in another context."""
    options = []
    for effect in L.case_effects(ledger, tol):
        component, held = effect["component"], other(effect["component"])
        if effect["case"] != weak_case or effect["factor"] == anchor["factors"][component]:
            continue
        if L.entry(ledger, effect["versus"])["factors"][component] != anchor["factors"][component]:
            continue  # the gain was measured against some other function, not against the anchor's own
        if effect["context"][held] == anchor["factors"][held]:
            continue  # same context: that program is already measured
        factors = dict(anchor["factors"])
        factors[component] = effect["factor"]
        if not _spliced(ledger, factors, considered):
            continue
        options.append({
            "kind": "transplant", "parent": anchor["id"], "component": component, "factors": factors,
            "donors": _source_for(ledger, factors), "evidence": [effect["evidence"]], "value": effect["mean_delta"],
            "question": "Does the %s of %s keep its %s gain (%+.2f, %d of %d seeds) under the anchor's %s?" % (
                component, effect["from"], weak_case, effect["mean_delta"], effect["credible_seeds"],
                effect["seeds"], held),
            "decides": {"if_target_met": "carry the transplanted %s forward" % component,
                        "if_not": "the gain depends on its original %s; edit the anchor instead" % held},
            "hypotheses": ["the %s of %s improves %s through a mechanism that does not depend on the %s" % (
                               component, effect["from"], weak_case, held),
                           "its %s gain came from the interaction with %s's own %s" % (weak_case, effect["from"], held)],
            "falsifier": "%s does not improve on most seeds against %s, or a protected design falls beyond its "
                         "tolerance" % (weak_case, anchor["id"])})
    unique = {}
    for row in sorted(options, key=lambda row: -row["value"]):
        unique.setdefault((row["factors"]["loss"], row["factors"]["decoder"]), row)
    return list(unique.values())


def removal_option(ledger, anchor, component, considered):
    """Undo the anchor's change to the function the next edit would modify, when that is unmeasured."""
    start = ledger["entries"][0]
    if anchor["id"] == "S" or not all(anchor["factors"][c] != start["factors"][c] for c in L.COMPONENTS):
        return None  # the anchor changes one function only: its parent already isolates it
    for control in L.removal_controls(ledger, anchor["id"]):
        if control["component"] != component or control["origin"] != "start" or control["status"] != "missing":
            continue
        if not _spliced(ledger, control["factors"], considered):
            return None
        parent = ledger["by_id"].get(anchor.get("parent") or "")
        context = ""
        if parent is not None and parent["complete"]:
            result = L.contrast(ledger, anchor["id"], parent["id"])
            context = " (its gain over %s is %+.2f, %d%% of it from exchanged dies)" % (
                parent["id"], result["official_delta"] or 0.0, round(100 * result["orientation_share"]))
        tolerance = L.aggregate_tolerance(ledger)
        return {
            "kind": "removal", "parent": anchor["id"], "component": component, "factors": control["factors"],
            "donors": _source_for(ledger, control["factors"]), "evidence": [], "value": 0.0,
            "question": "Does %s still need its %s change once its %s is fixed?" % (anchor["id"], component,
                                                                                    other(component)),
            "decides": {"if_within_tolerance": "build the next %s edit on the removal program" % component,
                        "if_worse": "keep the anchor's %s and edit its %s next" % (component, other(component))},
            "hypotheses": ["%s's %s change still contributes once its %s is in place" % (anchor["id"], component,
                                                                                        other(component)),
                           "%s's score is carried by its %s%s; the %s change adds nothing measurable" % (
                               anchor["id"], other(component), context, component)],
            "falsifier": "the first explanation fails if the removal scores within %.2f of %s; the second fails "
                         "if it scores more than %.2f below" % (tolerance, anchor["id"], tolerance)}
    return None


def _removal_follow_up(ledger, latest, tol):
    """After a measured removal: the parent and function its outcome selects."""
    experiment = latest.get("experiment") or {}
    anchor = ledger["by_id"].get(_label(ledger, experiment.get("parent") or "", experiment.get("parent_candidate")))
    if experiment.get("kind") != "removal" or not latest["complete"] or not anchor or not anchor["complete"]:
        return None
    delta = latest["score"] - anchor["score"]
    stored = (experiment.get("contract") or {}).get("tolerances")
    tolerance = L.aggregate_tolerance(ledger, stored or tol)  # the tolerance fixed when the removal was planned
    component = experiment["component"]
    if delta >= -tolerance:
        return {"anchor": anchor["id"], "parent": latest["id"], "component": component, "delta": round(delta, 4),
                "tolerance": tolerance,
                "conclusion": "the %s change of %s is not needed (%+.2f within %.2f)" % (component, anchor["id"],
                                                                                        delta, tolerance)}
    return {"anchor": anchor["id"], "parent": anchor["id"], "component": other(component), "delta": round(delta, 4),
            "tolerance": tolerance,
            "conclusion": "%s needs its %s change (%+.2f beyond %.2f); edit its %s" % (
                anchor["id"], component, delta, tolerance, other(component))}


def edit_reasoning(ledger, anchor, component, review, tol):
    """Two competing explanations for a model edit, and the outcome that separates them."""
    weak = review["weak"]["case"]
    tries = []
    for result in L.exact_contrasts(ledger, anchor["id"], tol):
        other_entry = L.entry(ledger, result["b"])
        if result["varies"] == [component] and other_entry.get("parent") == anchor["id"]:
            row = next(row for row in result["cases"] if row["case"] == weak)
            tries.append((result["b"], -row["mean_delta"] if row["mean_delta"] is not None else None))
    moved = ", ".join("%s %+.2f" % (label, delta) for label, delta in tries if delta is not None)
    return {
        "hypotheses": [
            "a %s change of %s can raise %s, whose mean is %+.2f against the start" % (
                component, anchor["id"], weak, review["weak"]["mean_delta"] or 0.0),
            ("%s does not respond to %s changes of %s: %d earlier tries moved it by %s" % (
                weak, component, anchor["id"], len(tries), moved)) if tries else
            ("the %s deficit comes from %s's %s, which this edit keeps" % (weak, anchor["id"], other(component)))],
        "distinguishes": "%s improves on most seeds against %s with every protected design inside its tolerance, "
                         "or it does not" % (weak, anchor["id"]),
        "falsifier": "%s does not improve on most seeds against %s, or a protected design (%s) falls more than its "
                     "tolerance below %s" % (weak, anchor["id"], ", ".join(
                         "%s %.2f" % (row["case"], row["tolerance"]) for row in review["protected"]
                         if row["case"] != weak) or "none", anchor["id"])}


def least_failed_component(ledger, label):
    """The function whose single-function children of `label` failed to beat it least often."""
    parent = L.entry(ledger, label)
    penalties = dict.fromkeys(L.COMPONENTS, 0)
    tries = dict.fromkeys(L.COMPONENTS, 0)
    for row in ledger["entries"]:
        if row.get("parent") != label or not row["complete"] or not row["factors"] or not parent["factors"]:
            continue
        changed = [c for c in L.COMPONENTS if row["factors"][c] != parent["factors"][c]]
        if len(changed) == 1:
            tries[changed[0]] += 1
            penalties[changed[0]] += row["score"] <= parent["score"] + L.SCORE_EPS
    own = [c for c, kind in (parent.get("footprint") or {}).items() if kind != "unchanged"]
    return min(L.COMPONENTS, key=lambda c: (penalties[c], tries[c], c in own))


def _declined_repair(ledger, decision, tol):
    """A branching repair whose protected gain lies inside this run's measured cell sensitivity."""
    gain = decision.get("protect_gain") or {}
    incumbent = ledger["by_candidate"].get(decision.get("incumbent_id"))
    if (decision.get("reason") != "targeted_repair" or gain.get("case") not in tol or incumbent is None
            or not incumbent["complete"] or not isinstance(gain.get("score_delta"), (int, float))):
        return None
    if gain["score_delta"] >= tol[gain["case"]]["cell"]:
        return None
    regression = decision.get("repair_regression") or {}
    child = ledger["by_candidate"].get(decision.get("incumbent_id"))
    lost = "its loss on %s/%s (%+.2f) is real" % (regression.get("case"), regression.get("seed"),
                                                  regression.get("score_delta") or 0.0)
    key = (regression.get("case"), str(regression.get("seed")))
    if key in incumbent["cells"]:
        if L.relation(ledger, L.entry(ledger, "S"), incumbent, key) == "exchange":
            lost += ", but %s's own value on that cell came from exchanged dies" % incumbent["id"]
        if abs(regression.get("score_delta") or 0.0) < tol[key[0]]["cell"]:
            lost += " and lies inside the same sensitivity"
    return {"evidence": "protect_gain:%s/%s" % (gain["case"], gain.get("seed")), "finding": "repair_declined",
            "parent": incumbent["id"], "component": least_failed_component(ledger, incumbent["id"]),
            "conclusion": "the gain to protect (%+.2f on %s/%s) is inside the %.2f-point cell sensitivity this run "
                          "measured for %s; extend the best program instead" % (
                              gain["score_delta"], gain["case"], gain.get("seed"), tol[gain["case"]]["cell"],
                              gain["case"]),
            "hypotheses": [
                "the child's gain on %s/%s (%+.2f) is a real effect of its edit and its loss on %s/%s (%+.2f) can be "
                "repaired without losing it" % (gain["case"], gain.get("seed"), gain["score_delta"],
                                                regression.get("case"), regression.get("seed"),
                                                regression.get("score_delta") or 0.0),
                "the gain to protect is within what small label changes do to %s here (median %.2f points per "
                "cell over %d pairs), so there is no measured gain for the repair to keep; %s" % (
                    gain["case"], tol[gain["case"]]["cell"], tol[gain["case"]]["pairs"], lost)],
            "distinguishes": "nothing: it spends the slot on %s instead. The test of the first explanation is the "
                             "repair itself, which the measured sensitivity makes a poor bet" % (
                                 child["id"] if child else "the best program")}


# ----------------------------------------------------------------------------------------------
# The decision after every evaluation


def lessons(ledger, tol):
    """Deterministic findings about the latest measured candidate, with evidence ids."""
    if len(ledger["entries"]) < 2:
        return []
    latest = ledger["entries"][-1]
    found = []
    affected = ["%s/%s" % key for key, cell in latest["cells"].items()
                if cell.get("failure") == "runtime_environment"]
    if affected:
        found.append({"finding": "environment_confounded", "evidence": latest["id"],
                      "conclusion": "Official penalties stand. These cells cannot attribute timing changes to "
                                    "the edit: " + ", ".join(affected)})
    if (latest.get("experiment") or {}).get("kind") == "orientation_control":
        cells = list(latest["cells"].values())
        verified = bool(cells) and all(cell.get("vs_start") == 1.0 and cell.get("status") == "succeeded"
                                       and cell.get("valid") is not False for cell in cells)
        found.append({"finding": "orientation_control_readback", "evidence": latest["id"],
                      "conclusion": ("All measured cells exchanged every tier label relative to the start." if verified
                                     else "The all-cell exchange is unverified. Do not credit this as a clean control.")})
    parent = ledger["by_id"].get(latest.get("parent") or "")
    if parent and latest["complete"] and parent["complete"]:
        result = L.contrast(ledger, latest["id"], parent["id"], tol)
        found.append({"evidence": result["id"], "finding": "paired_reading", "reading": L.gain_reading(result),
                      "official_delta": result["official_delta"], "orientation_share": result["orientation_share"],
                      "edit": latest.get("footprint")})
    contract = (latest.get("experiment") or {}).get("contract")
    if contract and _label(ledger, contract.get("anchor"), contract.get("anchor_candidate")) in ledger["by_id"]:
        verdict = judge(ledger, contract, latest["id"], tol)
        found.append({"evidence": "%s-%s" % (latest["id"], verdict["anchor"]), "finding": "plan_verdict", **verdict})
    duplicate = L.duplicate_of(ledger, latest["id"])
    if duplicate:
        found.append({"evidence": "%s=%s" % (latest["id"], duplicate["same_as"]), "finding": "duplicate_outcome",
                      **duplicate})
    for square in L.factorial_squares(ledger, tol):
        if latest["id"] in square["arms"].values():
            found.append({"evidence": "square:" + ",".join(square["arms"][name] for name in ("P", "A", "B", "AB")),
                          "finding": "factorial", "verdict": square["verdict"], "interaction": square["interaction"],
                          "loss_effect": square["loss_effect"], "decoder_effect": square["decoder_effect"],
                          "keep": square["arms"][square["keep"]]})
    follow = _removal_follow_up(ledger, latest, tol)
    if follow:
        found.append({"evidence": "%s-%s" % (latest["id"], follow["anchor"]), "finding": "removal", **follow})
    return found


def plan_next(ledger, baseline, remaining, total, considered=(), planning_calls=0):
    """The experiment to run next, the alternatives offered to a planner, and whether to call one.

    baseline: (parent candidate id, intent, decision) from search_control.select_next.
    considered: (loss id, decoder id) pairs of every program already proposed in this run.
    """
    parent_id, intent, decision = baseline
    tol = L.tolerances(ledger)
    considered = set(considered)
    found = lessons(ledger, tol)
    anchor = ledger["by_candidate"].get(parent_id)
    component = decision.get("component") or intent.split("_")[0]
    plan = {"baseline": {"parent": anchor["id"] if anchor else None, "intent": intent, "reason": decision.get("reason")},
            "lessons": found, "tolerances": tol, "budget": {"remaining": remaining, "total": total},
            "decision_override": None}
    if anchor is None or not anchor["complete"] or not anchor["factors"]:
        # Nothing measured to review: keep the branching choice, with no contract.
        edit = {"id": "X1", "kind": "edit", "parent": anchor["id"] if anchor else None, "parent_candidate": parent_id,
                "component": component, "question": None, "contract": None}
        plan.update(choice=edit, options=[edit], hard=[], review=None)
        return plan
    reason = decision.get("reason")
    # A mixed opening measures orientation only on some cells. Test its contribution across the matrix.
    entries = ledger["entries"]
    if len(entries) == 3 and reason not in KEEP_BASELINE:
        opening = entries[1]
        comparison = L.contrast(ledger, opening["id"], "S", tol)
        fractions = [cell.get("vs_start") for cell in opening["cells"].values()]
        if (opening["complete"] and comparison["varies"] == ["decoder"]
                and L.gain_reading(comparison) == "orientation_carried"
                and 1.0 in fractions and any(f is not None and f < 1.0 for f in fractions)
                and not any(row.get("failure") for row in opening["cells"].values())):
            start = entries[0]
            review = review_anchor(ledger, "S", tol)
            option = {"id": "X1", "kind": "orientation_control", "parent": "S",
                      "parent_candidate": start["candidate_id"], "component": "decoder",
                      "contract": make_contract(review, "decoder", tol, start["candidate_id"], "orientation_control"),
                      "opening_evidence": [{"case": row["case"], "seed": row["seed"], "score_delta": row["delta"],
                                            "changed_fraction": opening["cells"][(row["case"], row["seed"])]["vs_start"]}
                                           for row in comparison["cells"]],
                      "question": "Does changing only die orientation of the starting partition reproduce the gain?",
                      "hypotheses": ["Die orientation explains the gain.", "Regrouping or its interaction is needed."],
                      "distinguishes": "Keep the loss and the unordered partition identical to the official start. "
                                       "Exchange the two die labels consistently. Compare each measured cell with "
                                       "the start and the opening on the same case and seed.",
                      "falsifier": "Any changed unordered grouping invalidates this control; a valid exchange "
                                   "that fails to reproduce the opening gain weakens the orientation explanation."}
            found.append({"finding": "opening_orientation", "evidence": comparison["id"],
                          "conclusion": "Share of positive paired score movement carried by exchanged or "
                                        "near-exchanged cells: %.3f" % comparison["orientation_share"]})
            plan.update(choice=option, options=[option], hard=[], review=review,
                        decision_override={"reason": "orientation_control", "incumbent_id": decision.get("incumbent_id")})
            return plan
    follow = next((row for row in found if row["finding"] == "removal"), None)
    declined = _declined_repair(ledger, decision, tol)
    if declined:
        found.append(declined)
    override = follow if follow and reason not in KEEP_BASELINE else declined
    if override:
        anchor, component = L.entry(ledger, override["parent"]), override["component"]
        reason = "extend_best" if override is declined else "removal_follow_up"
        plan["decision_override"] = {"reason": reason, "note": override["conclusion"],
                                     "incumbent_id": decision.get("incumbent_id")}
    review = review_anchor(ledger, anchor["id"], tol)
    if reason == "targeted_repair" and (decision.get("repair_regression") or {}).get("case"):
        # The branching repair already names the regression and the gain to keep; use the same target.
        review = retarget(review, decision["repair_regression"]["case"],
                          (decision.get("protect_gain") or {}).get("case"), tol)
    edit = {"kind": "edit", "parent": anchor["id"], "component": component,
            "contract": make_contract(review, component, tol, anchor["candidate_id"]),
            "question": "Can a %s change of %s raise %s without losing %s?" % (
                component, anchor["id"], review["weak"]["case"],
                ", ".join(row["case"] for row in review["protected"] if row["case"] != review["weak"]["case"]) or
                "its other designs"),
            **edit_reasoning(ledger, anchor, component, review, tol)}
    if override is declined and declined:
        edit.update(hypotheses=declined["hypotheses"], distinguishes=declined["distinguishes"])
    options = []
    splices_used = sum((row.get("experiment") or {}).get("kind") in SPLICES for row in ledger["entries"])
    latest_kind = (ledger["entries"][-1].get("experiment") or {}).get("kind") if len(ledger["entries"]) > 1 else None
    plan["budget"].update(splices_used=splices_used, splice_cap=max(1, total // 3))
    if (reason not in KEEP_BASELINE and remaining >= 1
            and splices_used < max(1, total // 3) and latest_kind not in SPLICES):
        # Ranked: a merge of two credited gains, then a transplant for the weak design, then a removal
        # that selects the next parent. A removal needs a later slot to act on its answer.
        options.extend(merge_options(ledger, tol, considered)[:1])
        options.extend(transplant_options(ledger, anchor, review["weak"]["case"], tol, considered)[:1])
        removal = (removal_option(ledger, anchor, component, considered)
                   if remaining >= 2 and reason == "extend_best" and not follow else None)
        if removal:
            options.append(removal)
    unique = []
    for option in options:  # a merge and a transplant can name the same program
        if all(option["factors"] != kept["factors"] for kept in unique):
            unique.append(option)
    options = unique[:2]
    for option in options:
        option["contract"] = make_contract(review_anchor(ledger, option["parent"], tol), option["component"], tol,
                                           L.entry(ledger, option["parent"])["candidate_id"], option["kind"])
        option.setdefault("distinguishes", "its outcome selects between the two branches of `decides`")
    options.append(edit)
    departs = bool(override) or (options[0]["kind"] in SPLICES)
    baseline_anchor = ledger["by_candidate"].get(parent_id)
    if PLAN_ON_OVERRIDE and departs and baseline_anchor is not None and not any(
            option["kind"] == "edit" and option["parent"] == baseline_anchor["id"] and option["component"] ==
            (decision.get("component") or intent.split("_")[0]) for option in options):
        base_component = decision.get("component") or intent.split("_")[0]
        base_review = review_anchor(ledger, baseline_anchor["id"], tol)
        options.append({"kind": "edit", "parent": baseline_anchor["id"], "component": base_component, "baseline": True,
                        "contract": make_contract(base_review, base_component, tol, baseline_anchor["candidate_id"]),
                        "question": "The branching choice: a %s change of %s (%s)." % (
                            base_component, baseline_anchor["id"], decision.get("reason")),
                        **edit_reasoning(ledger, baseline_anchor, base_component, base_review, tol)})
    hard = []
    for row in found:
        if row["finding"] == "plan_verdict" and row.get("verdict") in CONTRADICTED:
            hard.append("plan_contradicted")
        if row["finding"] == "plan_verdict" and any(cell["beyond_cell_tolerance"]
                                                    for cell in row.get("protected_regressions", [])):
            hard.append("protected_regression")
        if row["finding"] == "factorial" and row["verdict"] == "antagonistic":
            hard.append("antagonistic_combination")
        if row["finding"] == "duplicate_outcome":
            hard.append("duplicate_outcome")
    if reason in ("switch_branch", "reopen_official_start"):
        hard.append("stalled_branch")
    if PLAN_ON_OVERRIDE and departs:
        hard.append("rolling_override")
    if planning_calls >= MAX_PLANNING_CALLS or reason in KEEP_BASELINE:
        hard = []
    if hard and len(options) == 1:
        # A planning call needs a real choice: offer the competing edit as well.
        incumbent = ledger["by_candidate"].get(decision.get("incumbent_id"))
        if incumbent and incumbent["complete"] and incumbent["factors"] and incumbent["id"] != anchor["id"]:
            alternative, alternative_component = incumbent, least_failed_component(ledger, incumbent["id"])
        else:
            alternative, alternative_component = anchor, other(component)
        options.append({"kind": "edit", "parent": alternative["id"], "component": alternative_component,
                        "contract": make_contract(review_anchor(ledger, alternative["id"], tol), alternative_component,
                                                  tol, alternative["candidate_id"]),
                        "question": "Is a %s change of %s more promising than the edit above?" % (
                            alternative_component, alternative["id"])})
    for index, option in enumerate(options, 1):
        option["id"] = "X%d" % index
    for option in options:
        option["parent_candidate"] = L.entry(ledger, option["parent"])["candidate_id"]
    plan.update(choice=options[0], options=options, hard=sorted(set(hard)), review=review)
    return plan


def splice_source(loss_source, decoder_source):
    """One program with the loss function of one measured program and the decoder of another.

    The function texts are copied verbatim, docstrings included; the official validator still
    checks the result before anything is submitted.
    """
    def segment(source, index):
        functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
        if len(functions) != len(L.COMPONENTS):
            raise ValueError("A splice donor must contain exactly the two editable functions")
        node = functions[index]
        return "\n".join(source.splitlines()[node.lineno - 1:node.end_lineno])
    return ("# EVOLVE-BLOCK-START\n" + segment(loss_source, 0) + "\n\n\n" + segment(decoder_source, 1)
            + "\n# EVOLVE-BLOCK-END\n")


def splice_hypothesis(option):
    """The changed-component record for a splice, in the docstring fields the search log keeps."""
    target = (option.get("contract") or {}).get("target")
    falsifier = option.get("falsifier") or (
        "target case %s does not improve" % target["case"] if target else "see the decision table")
    return {"mechanism": "%s splice: %s from %s" % (option["kind"], option["component"],
                                                   option["donors"][option["component"]]),
            "decision": option["question"][:180],
            "prediction": "; ".join("%s: %s" % item for item in sorted(option["decides"].items()))[:180],
            "falsifier": falsifier[:180]}


# ----------------------------------------------------------------------------------------------
# Model-facing views


PLAN_TASK = """You plan one official experiment for a TP-GNN loss/decoder search. Do not write code.
Reply with one JSON object: {"choice": "<option id>", "explanations": ["<H1>", "<H2>"],
"discriminating_prediction": "...", "falsifier": "...", "edit_brief": "...",
"expected_footprint": "structural" | "coefficients_only" | "either", "probe": null}.
Choose exactly one offered option. Give two competing explanations of the latest evidence and the
outcome of the chosen experiment that would separate them. For an edit, `edit_brief` states the
single change in at most 60 words; for a splice it may be empty. `probe` may name one allowed
synthetic check from `allowed_probes`, or be null. Evidence ids such as R3-S name paired
comparisons. Case and seed names are evidence labels only; never propose rules keyed to them.
Labels that only exchange the two dies, published start values and timing changes with identical
labels are confounded evidence. Keep the whole reply under 200 words."""


def planner_request(plan, packet, allowed_probes):
    return {"options": [{key: option.get(key) for key in ("id", "kind", "parent", "component", "question", "decides",
                                                          "hypotheses", "distinguishes", "falsifier")}
                        for option in plan["options"]],
            "triggers": plan["hard"], "lessons": packet["lessons"], "anchor_review": packet["anchor_review"],
            "budget": plan["budget"], "allowed_probes": allowed_probes}


def parse_plan_reply(text, plan):
    """The planner's JSON, checked against the offered options; ValueError when unusable."""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("The planning reply contains no JSON object")
    try:
        reply = json.loads(match.group(0))
    except ValueError as error:
        raise ValueError("The planning reply is not valid JSON") from error
    options = {option["id"]: option for option in plan["options"]}
    if not isinstance(reply, dict) or reply.get("choice") not in options:
        raise ValueError("The planning reply did not choose an offered option")
    explanations = reply.get("explanations")
    if not isinstance(explanations, list) or len(explanations) < 2 or not all(isinstance(x, str) and x.strip()
                                                                              for x in explanations[:2]):
        raise ValueError("The planning reply needs two competing explanations")
    cleaned = {"choice": reply["choice"], "explanations": [" ".join(x.split())[:240] for x in explanations[:2]]}
    for key in ("discriminating_prediction", "falsifier", "edit_brief"):
        value = reply.get(key)
        cleaned[key] = " ".join(value.split())[:400] if isinstance(value, str) else ""
    cleaned["probe"] = reply.get("probe") if isinstance(reply.get("probe"), dict) else None
    shape = reply.get("expected_footprint")
    cleaned["expect_footprint"] = ([shape] if shape in ("structural", "coefficients_only") else None)
    return cleaned


TRIAL_METRICS = ("final_global_wns_setup_ns", "final_global_tns_setup_ns", "cut_net_count", "timing_weighted_cut",
                 "tp_gnn_repair_moved_area_fraction")
# Candidate scores and statuses already appear once in the trial's own cells.
PAIR_FIELDS = ("case", "seed", "parent_score", "score_delta", "wns_slack_delta_ns", "tns_slack_delta_ns",
               "cut_nets_delta", "score_delta_terms", "observation", "failure")
COMPARISON_FIELDS = ("parent_id", "candidate_id", "parent_source", "complete", "expected_cells", "scored_pairs",
                     "official_score_delta", "improved_pairs", "regressed_pairs", "largest_gain", "largest_regression",
                     "candidate_invalid_cells", "failure_counts", "assignment_pairs_verified",
                     "timing_changes_with_identical_assignment", "cases")


def _compact_comparison(comparison, with_cells):
    if not isinstance(comparison, dict) or "cells" not in comparison:
        return comparison  # None, a status record or a same_as pointer
    result = {key: comparison[key] for key in COMPARISON_FIELDS if key in comparison}
    if with_cells:
        cells = []
        for row in comparison["cells"]:
            cell = {key: row[key] for key in PAIR_FIELDS if row.get(key) is not None}
            assignment = row.get("assignment") or {}
            if assignment.get("changed_fraction") is not None:
                cell["labels_changed_fraction"] = assignment["changed_fraction"]
            if assignment.get("flip_adjusted_changed_fraction") is not None:
                cell["grouping_changed_fraction_up_to_tier_exchange"] = assignment["flip_adjusted_changed_fraction"]
            cells.append(cell)
        result["cells"] = cells
    return result


def rounded(value, digits=6):
    """Floats to `digits` significant digits, recursively, for model-facing JSON only."""
    if isinstance(value, float):
        return float("%.*g" % (digits, value)) if value == value and abs(value) != float("inf") else value
    if isinstance(value, dict):
        return {key: rounded(item, digits) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(item, digits) for item in value]
    return value


def compact_trial(summary):
    """The latest receipt summary without repeated or diagnostic-only fields.

    Keeps every official cell score, status and failure, the WNS/TNS values, the paired comparison with
    the actual parent cell by cell, and only the totals of the comparison with the published start
    (the anchor review carries the same-host start cell by cell).
    """
    if not isinstance(summary, dict):
        return summary
    result = {key: summary[key] for key in ("request_id", "candidate_id", "status", "reason", "score", "case_scores",
                                            "diagnostics_unavailable") if key in summary}
    attempt = summary.get("attempt") or {}
    result["attempt"] = {key: attempt[key] for key in ("parent_id", "search_intent", "policy_action",
                                                       "changed_components") if key in attempt}
    if (attempt.get("preflight") or {}).get("probes"):
        result["attempt"]["synthetic_probes"] = attempt["preflight"]["probes"]
    cells = []
    for cell in summary.get("cells") or []:
        row = {key: cell[key] for key in ("case", "seed", "score", "valid", "status", "reason", "failure") if key in cell}
        if cell.get("raw_score") is not None and cell["raw_score"] != cell.get("score"):
            row["raw_score_before_floor"] = cell["raw_score"]
        metrics = cell.get("metrics") or {}
        row.update((key, metrics[key]) for key in TRIAL_METRICS if key in metrics)
        change = cell.get("partition_change_vs_initial") or {}
        if "partition_assignment_changed_fraction" in change:
            row["moved_fraction_vs_start"] = change["partition_assignment_changed_fraction"]
        cells.append(row)
    result["cells"] = cells
    result["parent_comparison"] = _compact_comparison(summary.get("parent_comparison"), True)
    result["initial_comparison"] = _compact_comparison(summary.get("initial_comparison"), False)
    return rounded(result)


def compact_prior(rows, labels):
    """prior_trials with ledger ids, the edited mechanism only and no structural hashes."""
    result = []
    for row in rows or []:
        notes = row.get("changed_components") or {}
        result.append({
            "evidence_id": labels.get(row.get("candidate_id")), "parent": labels.get(row.get("parent_id")),
            "changed": {component: (value.get("mechanism") if isinstance(value, dict) else str(value))[:160]
                        for component, value in notes.items()},
            "status": row.get("status"), "score": row.get("score"), "paired_score_delta": row.get("paired_score_delta"),
            "inert_evidence": row.get("inert_evidence")})
    return result


# The experiment block replaces these per-round views; the same facts appear there once.
REPLACED_BY_EXPERIMENT = ("decision_evidence", "earlier_edits_from_selected_parent")


def assemble_request(request, packet=None, planned=None, labels=None, parent_is_last=False):
    """The generation request: the Agent's fields compacted, plus the checked experiment and plan."""
    result = dict(request)
    result["last_trial"] = compact_trial(request.get("last_trial"))
    if parent_is_last and request.get("parent_feedback") is not None:
        result["parent_feedback"] = {"same_as": "last_trial"}
    if labels is not None:
        result["prior_trials"] = compact_prior(request.get("prior_trials"), labels)
    if packet is not None:
        result["experiment"] = packet
        for key in REPLACED_BY_EXPERIMENT:
            result.pop(key, None)
    if planned is not None:
        result["experiment_plan"] = {key: planned.get(key) for key in (
            "explanations", "discriminating_prediction", "falsifier", "edit_brief")}
    return {key: (value if key == "parent_program" else rounded(value)) for key, value in result.items()}


def compact_lesson(row):
    keep = ("evidence", "finding", "reading", "official_delta", "edit", "verdict", "same_as", "basis", "interaction",
            "keep", "conclusion", "loss_effect", "decoder_effect", "parent", "component")
    result = {key: row[key] for key in keep if key in row}
    if row.get("finding") == "plan_verdict":
        result["target"] = {key: row.get("target", {}).get(key) for key in ("case", "mean_delta", "met")}
        result["protected_regressions"] = [{"cell": cell["cell"], "delta": cell["delta"]}
                                           for cell in row.get("protected_regressions", [])[:4]]
    return result


def generation_packet(plan, option, ledger, tol=None):
    """Exactly the evidence handed to code generation for one chosen experiment."""
    tol = tol or plan["tolerances"]
    review = review_anchor(ledger, option["parent"], tol)
    comparisons = []
    for result in sorted(L.exact_contrasts(ledger, option["parent"], tol),
                         key=lambda result: (result["varies"] != [option["component"]],
                                             -(ledger["entries"].index(L.entry(ledger, result["b"]))))):
        if len(comparisons) == 3:
            break
        if result["b"] == "S":
            continue
        comparisons.append({"evidence": result["id"], "varies": result["varies"][0],
                            "official_delta": result["official_delta"], "reading": L.gain_reading(result),
                            "case_mean_deltas": {row["case"]: row["mean_delta"] for row in result["cases"]}})
    return {
        "experiment": {key: option.get(key) for key in ("id", "kind", "parent", "component", "question",
                                                        "hypotheses", "distinguishes", "falsifier", "opening_evidence")
                       if option.get(key) is not None},
        "contract": option.get("contract"),
        "anchor_review": {key: review[key] for key in ("anchor", "official_delta", "reading", "weak", "protected",
                                                        "fragile", "rows")},
        "comparisons": comparisons,
        "lessons": [compact_lesson(row) for row in plan["lessons"]],
    }
