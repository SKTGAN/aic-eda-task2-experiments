"""Evidence ledger for the rolling search: exact factors, paired cells and reusable controls.

Standard-library code for the Python 3.8 Agent runtime. It reads only this run's own receipt
summaries and accepted sources; it never calls the bridge, the model or the evaluator. Case and seed
labels are evidence keys. Nothing here turns them into rules for generated programs.

A program is a pair of factors: the exact loss body and the exact decoder body, docstrings removed.
Every evaluated program is one point in that grid, so a control is any other measured point that
shares one factor. A contrast is exact when the two programs differ in exactly one function.
"""

import ast
import hashlib
from math import isfinite, sqrt


COMPONENTS = ("loss", "decoder")
EXCHANGE_FRACTION = 0.5     # more than half of the instances moved: the same grouping with the dies exchanged
LOCAL_FRACTION = 0.10       # at most this share moved, after undoing an exchange: a local boundary change
SCORE_EPS = 1e-6
TIME_EPS = 1e-6
# Sensitivity heuristics, not measurement noise. The physical flow is deterministic for a fixed
# assignment (identical labels gave identical timing in every archived repeat), so these numbers
# describe how far a cell's score moves when its labels move a little. They are policy settings.
DEFAULT_TOLERANCE = 5.0     # case-mean score points before the run has calibration pairs
MIN_TOLERANCE = 2.0
CALIBRATION_PAIRS = 3       # local label perturbations of one case needed before the tolerance is calibrated
SENSITIVITY_QUANTILE = 0.5  # quantile of the absolute score changes over local pairs (the median)
TOLERANCE_SCALE = 1.0       # multiplies every calibrated tolerance
ROOT_SEEDS = True           # a case-mean tolerance divides the cell sensitivity by sqrt(seeds)
NARROW_SHARE = 0.75         # one cell carrying this share of an official gain makes the gain narrow
ORIENTATION_SHARE = 0.5     # exchanged cells carrying this share of the positive change make it orientation


def number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value):
        return float(value)
    return None


def cell_key(cell):
    return cell["case"], str(cell["seed"])


# ----------------------------------------------------------------------------------------------
# Exact factors


def _strip_docstring(function):
    if ast.get_docstring(function, clean=False) is not None:
        function.body.pop(0)
    return function


class _DropScaling(ast.NodeTransformer):
    """`c * x`, `x * c` and `x / c` with a numeric literal c become `x`: a scale is a coefficient."""

    @staticmethod
    def _literal(node):
        return isinstance(node, ast.Constant) and type(node.value) in (int, float)

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Mult) and self._literal(node.left) and not self._literal(node.right):
            return node.right
        if isinstance(node.op, (ast.Mult, ast.Div)) and self._literal(node.right) and not self._literal(node.left):
            return node.left
        return node


def _structure(function):
    """The function with literal scales dropped, numeric literals zeroed and local names renamed
    (subscript selectors kept)."""
    function = _DropScaling().visit(function)
    nodes = list(ast.walk(function))
    assigned = {node.id for node in nodes if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
    selectors = {id(index) for node in nodes if isinstance(node, ast.Subscript)
                 for index in ast.walk(node.slice) if isinstance(index, ast.Constant)}
    names = {}
    for node in nodes:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float) and id(node) not in selectors:
            node.value = 0
        elif isinstance(node, ast.Name) and node.id in assigned:
            node.id = names.setdefault(node.id, "__local_%d" % len(names))
    return function


def function_dumps(source, structure=False):
    """Canonical dump of each editable function without its docstring (the Agent's function_keys)."""
    dumps = []
    for function in ast.parse(source).body:
        if not isinstance(function, ast.FunctionDef):
            continue
        function = _strip_docstring(function)
        if structure:
            function = _structure(function)
        dumps.append(ast.dump(function, include_attributes=False))
    if len(dumps) != len(COMPONENTS):
        raise ValueError("Expected exactly the loss and decoder functions")
    return tuple(dumps)


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def factor_ids(source):
    """Exact identity of each function body: equal ids mean the same code after removing docstrings."""
    return dict(zip(COMPONENTS, (_digest(dump) for dump in function_dumps(source))))


def factor_pair(keys):
    """(loss id, decoder id) from the Agent's function_keys tuple of one program."""
    return tuple(_digest(dump) for dump in keys)


def edit_footprint(parent_source, source):
    """Per function: unchanged, coefficients_only (same structure, other constants) or structural."""
    exact = zip(function_dumps(parent_source), function_dumps(source))
    shape = zip(function_dumps(parent_source, True), function_dumps(source, True))
    result = {}
    for component, (old, new), (old_shape, new_shape) in zip(COMPONENTS, exact, shape):
        if old == new:
            result[component] = "unchanged"
        elif old_shape == new_shape:
            result[component] = "coefficients_only"
        else:
            result[component] = "structural"
    return result


# ----------------------------------------------------------------------------------------------
# Start reference


def same_host_start(published, summaries):
    """The published start, with each cell replaced by this host's measurement where a receipt kept the
    start assignment (the organizer diagnostic reports zero changed instances on that cell).

    A fixed assignment gives the same timing on one host, so such a cell is the start's own timing
    here. Two such cells that disagree leave the published value. Borrowed from the two-stage Harness.
    """
    if published is None:
        return None
    keys = {cell_key(cell) for cell in published["feedback"]["cells"]}
    measured, conflicts = {}, set()
    for summary in summaries:
        if summary.get("status") != "succeeded":
            continue
        for cell in summary.get("cells") or []:
            key = cell_key(cell)
            change = cell.get("partition_change_vs_initial") or {}
            if (key not in keys or key in conflicts or change.get("partition_assignment_changed_count") != 0
                    or cell.get("status") != "succeeded" or number(cell.get("score")) is None):
                continue
            previous = measured.get(key)
            if previous is not None:
                if not _timing_equal(_cell_record(previous), _cell_record(cell)):
                    conflicts.add(key)
                    del measured[key]
                continue
            measured[key] = cell
    if not measured and not conflicts:
        return published
    cells = []
    for cell in published["feedback"]["cells"]:
        same = measured.get(cell_key(cell))
        cells.append({**cell, "score": same["score"], "metrics": same.get("metrics") or {}, "measured_on": "this_host"}
                     if same else {**cell, "measured_on": "published"})
    cases = []
    for cell in cells:
        if cell["case"] not in cases:
            cases.append(cell["case"])
    score = sum(sum(c["score"] for c in cells if c["case"] == case) / sum(1 for c in cells if c["case"] == case)
                for case in cases) / len(cases)
    return {**published, "feedback": {"score": score, "cells": cells},
            "summary": {"same_host_cells": len(measured), "published_cells": len(cells) - len(measured),
                        "same_host_score": score, "published_score": published["feedback"]["score"],
                        "score_kind": "measured" if len(measured) == len(cells) else "mixed_reference",
                        "conflicting_cells_using_published": [list(key) for key in sorted(conflicts)]}}


# ----------------------------------------------------------------------------------------------
# Ledger entries


def _cell_record(cell, fingerprint=None, measured_on=None):
    metrics = cell.get("metrics") or {}
    change = cell.get("partition_change_vs_initial") or {}
    count = change.get("partition_assignment_changed_count")
    fraction = number(change.get("partition_assignment_changed_fraction"))
    if count == 0:
        fraction = 0.0
    record = {
        "score": number(cell.get("score")),
        "wns": number(metrics.get("final_global_wns_setup_ns")),
        "tns": number(metrics.get("final_global_tns_setup_ns")),
        "valid": cell.get("valid"),
        "status": cell.get("status"),
        "vs_start": fraction,
        "failure": (cell.get("failure") or {}).get("kind"),
        "labels": (fingerprint or {}).get("labels"),
        "grouping": (fingerprint or {}).get("grouping"),
    }
    if measured_on:
        record["measured_on"] = measured_on
    return record


def _parent_pairs(summary):
    """Exact label distance to the entry's own parent, when the Agent could align the label files."""
    pairs = {}
    for row in (summary.get("parent_comparison") or {}).get("cells") or []:
        assignment = row.get("assignment") or {}
        if assignment.get("source") != "published_aligned_assignments":
            continue
        pairs[cell_key(row)] = {"changed_fraction": number(assignment.get("changed_fraction")),
                                "flip_adjusted_fraction": number(assignment.get("flip_adjusted_changed_fraction")),
                                "identical": assignment.get("identical") is True}
    return pairs


def start_entry(start, factors, schedule):
    """The official start: published cells, replaced by this host's measurement where one exists."""
    cells = {}
    for cell in (start.get("feedback") or {}).get("cells") or []:
        on_host = cell.get("measured_on") == "this_host"
        record = _cell_record({**cell, "partition_change_vs_initial": {"partition_assignment_changed_count": 0}},
                              measured_on="this_host" if on_host else "published")
        record["valid"], record["status"] = True, "succeeded" if on_host else "published_reference"
        cells[cell_key(cell)] = record
    keys = [cell_key(cell) for cell in schedule]
    return {"id": "S", "candidate_id": start.get("candidate_id"), "request_id": None, "parent_id": None,
            "factors": dict(factors), "score": number((start.get("feedback") or {}).get("score")),
            "complete": all(key in cells and cells[key]["score"] is not None for key in keys),
            "measured": all(key in cells and cells[key].get("measured_on") == "this_host" for key in keys),
            "cells": cells, "pairs": {}, "attempt": {}, "action": "official_start", "experiment": None}


def build_ledger(summaries, sources, schedule, start, initial_source, fingerprints=None):
    """One entry per receipt, in evaluation order, after the start entry `S`.

    summaries: the Agent's chronological receipt summaries; sources: {request_id: accepted source};
    start: the start reference (published or same-host); fingerprints: {request_id: {(case, seed):
    {"labels", "grouping"}}} from the published label files, when the Agent could read them.
    """
    keys = [cell_key(cell) for cell in schedule]
    if not keys or len(set(keys)) != len(keys):
        raise ValueError("Expected a nonempty schedule with unique case/seed pairs")
    initial = factor_ids(initial_source)
    entries = [start_entry(start, initial, schedule)]
    by_candidate = {entries[0]["candidate_id"]: entries[0]}
    for index, summary in enumerate(summaries, 1):
        source = sources.get(summary.get("request_id"))
        try:
            factors = factor_ids(source) if source else None
        except (SyntaxError, ValueError):
            factors = None
        prints = (fingerprints or {}).get(summary.get("request_id")) or {}
        cells = {}
        for cell in summary.get("cells") or []:
            cells[cell_key(cell)] = _cell_record(cell, prints.get(cell_key(cell)))
        complete = (summary.get("status") == "succeeded" and number(summary.get("score")) is not None
                    and set(cells) == set(keys) and all(cells[key]["score"] is not None for key in keys))
        attempt = summary.get("attempt") or {}
        entry = {
            "id": "R%d" % index, "candidate_id": summary.get("candidate_id"),
            "request_id": summary.get("request_id"), "parent_id": attempt.get("parent_id"),
            "factors": factors, "score": number(summary.get("score")), "complete": complete,
            "measured": complete and all(cells[key]["valid"] is True and cells[key]["status"] == "succeeded"
                                         for key in keys),
            "cells": cells, "pairs": _parent_pairs(summary), "attempt": attempt,
            "action": attempt.get("policy_action") or attempt.get("search_intent"),
            "experiment": attempt.get("experiment"),
        }
        entries.append(entry)
        if entry["candidate_id"]:
            by_candidate[entry["candidate_id"]] = entry
    sources = dict(sources)
    sources[None] = initial_source  # the start entry has no request id
    for entry in entries[1:]:
        parent = by_candidate.get(entry["parent_id"])
        entry["parent"] = parent["id"] if parent else None
        before, after = sources.get(parent["request_id"]) if parent else None, sources.get(entry["request_id"])
        try:
            entry["footprint"] = edit_footprint(before, after) if before and after else None
        except (SyntaxError, ValueError):
            entry["footprint"] = None
    return {"entries": entries, "by_id": {entry["id"]: entry for entry in entries},
            "by_candidate": by_candidate, "schedule": keys,
            "cases": sorted({case for case, _ in keys}, key=[case for case, _ in keys].index)}


def entry(ledger, label):
    return ledger["by_id"][label]


def find_program(ledger, factors):
    """A complete entry with exactly these two factors (the start included), preferring one measured
    on this host on every cell."""
    matches = [row for row in ledger["entries"] if row["factors"] == factors and row["complete"]]
    return next((row for row in matches if row["measured"]), matches[0] if matches else None)


# ----------------------------------------------------------------------------------------------
# Assignment relation between two entries on one cell


def _side_and_distance(fraction):
    return fraction > EXCHANGE_FRACTION, min(fraction, 1.0 - fraction)


def relation(ledger, a, b, key):
    """identical, exchange, local, regroup or unknown: how b's labels on one cell differ from a's."""
    ca, cb = a["cells"].get(key), b["cells"].get(key)
    if ca is None or cb is None:
        return "unknown"
    if ca["labels"] and cb["labels"]:
        if ca["labels"] == cb["labels"]:
            return "identical"
        if ca["grouping"] == cb["grouping"]:
            return "exchange"
    for child, parent in ((a, b), (b, a)):
        pair = child["pairs"].get(key) if child.get("parent") == parent["id"] else None
        if pair and pair["changed_fraction"] is not None:
            if pair["identical"]:
                return "identical"
            flipped = pair["flip_adjusted_fraction"]
            if flipped is not None and flipped <= LOCAL_FRACTION:
                return "exchange" if pair["changed_fraction"] > EXCHANGE_FRACTION else "local"
            return "regroup"
    fa, fb = ca["vs_start"], cb["vs_start"]
    if fa is None or fb is None:
        return "unknown"
    if fa == 0.0 and fb == 0.0:
        return "identical"
    (side_a, da), (side_b, db) = _side_and_distance(fa), _side_and_distance(fb)
    if da <= LOCAL_FRACTION and db <= LOCAL_FRACTION:
        return "exchange" if side_a != side_b else "local"
    if abs(da - db) > LOCAL_FRACTION:
        return "regroup"
    return "unknown"


def _timing_equal(ca, cb):
    values = [(ca[name], cb[name]) for name in ("score", "wns", "tns")]
    return all(x is not None and y is not None and abs(x - y) <= TIME_EPS for x, y in values)


# ----------------------------------------------------------------------------------------------
# Calibration


def _cell_pairs(ledger):
    """Every pair of entries measured on this host, cell by cell, with their label relation."""
    rows = [row for row in ledger["entries"] if row["id"] != "S" and row["measured"]]
    start = ledger["entries"][0]
    for key in ledger["schedule"]:
        group = rows + ([start] if start["cells"].get(key, {}).get("measured_on") == "this_host" else [])
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                ca, cb = group[i]["cells"][key], group[j]["cells"][key]
                if ca["score"] is not None and cb["score"] is not None:
                    yield key, group[i], group[j], relation(ledger, group[i], group[j], key)


def sensitivity_pairs(ledger):
    """Raw calibration observations: two programs whose labels on a cell differ only locally (same
    orientation, each within LOCAL_FRACTION of one grouping) and whose timing differs."""
    pairs = []
    for key, a, b, rel in _cell_pairs(ledger):
        ca, cb = a["cells"][key], b["cells"][key]
        if rel == "local" and not _timing_equal(ca, cb):
            pairs.append({"case": key[0], "seed": key[1], "a": a["id"], "b": b["id"],
                          "moved_vs_start": [ca["vs_start"], cb["vs_start"]],
                          "scores": [ca["score"], cb["score"]], "abs_delta": abs(ca["score"] - cb["score"])})
    return pairs


def repeat_pairs(ledger):
    """Matched repeats: two receipts with identical labels on a cell, and whether their timing agrees."""
    pairs = []
    for key, a, b, rel in _cell_pairs(ledger):
        if rel == "identical":
            ca, cb = a["cells"][key], b["cells"][key]
            pairs.append({"case": key[0], "seed": key[1], "a": a["id"], "b": b["id"],
                          "basis": "labels" if ca["labels"] and cb["labels"] else "zero_changed_vs_start",
                          "identical_timing": _timing_equal(ca, cb), "abs_delta": abs(ca["score"] - cb["score"])})
    return pairs


def quantile(values, q):
    """Linear-interpolation quantile of a non-empty list."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def tolerances(ledger):
    """Case-mean tolerance from this run's own local label perturbations (a sensitivity heuristic).

    The SENSITIVITY_QUANTILE of the absolute score changes over a case's sensitivity_pairs is its
    cell sensitivity; a mean over the case's seeds divides it by sqrt(seeds) when ROOT_SEEDS holds.
    Fewer than CALIBRATION_PAIRS pairs leave the explicit DEFAULT_TOLERANCE.
    """
    pairs = sensitivity_pairs(ledger)
    result = {}
    for case in ledger["cases"]:
        seeds = sum(1 for key in ledger["schedule"] if key[0] == case)
        divisor = sqrt(seeds) if ROOT_SEEDS else 1.0
        changes = [row["abs_delta"] for row in pairs if row["case"] == case]
        if len(changes) >= CALIBRATION_PAIRS:
            cell = quantile(changes, SENSITIVITY_QUANTILE) * TOLERANCE_SCALE
            result[case] = {"cell": round(cell, 3), "case_mean": round(max(MIN_TOLERANCE, cell / divisor), 3),
                            "pairs": len(changes), "source": "calibrated"}
        else:
            result[case] = {"cell": round(DEFAULT_TOLERANCE * divisor, 3), "case_mean": DEFAULT_TOLERANCE,
                            "pairs": len(changes), "source": "default"}
    return result


def aggregate_tolerance(ledger, tol=None):
    """Tolerance for the official score, the mean of the case means."""
    tol = tol or tolerances(ledger)
    values = [tol[case]["case_mean"] for case in ledger["cases"]]
    return round(sqrt(sum(value * value for value in values)) / len(values), 3)


# ----------------------------------------------------------------------------------------------
# Contrasts


def contrast(ledger, a_id, b_id, tol=None):
    """Paired evidence that `a` (the changed program) differs from `b` (its control) on every cell."""
    a, b = entry(ledger, a_id), entry(ledger, b_id)
    tol = tol or tolerances(ledger)
    varies = ([component for component in COMPONENTS if a["factors"][component] != b["factors"][component]]
              if a["factors"] and b["factors"] else None)
    rows = []
    for key in ledger["schedule"]:
        ca, cb = a["cells"].get(key), b["cells"].get(key)
        row = {"case": key[0], "seed": key[1]}
        if not ca or not cb or ca["score"] is None or cb["score"] is None:
            row.update(delta=None, strength="missing")
            rows.append(row)
            continue
        rel = relation(ledger, a, b, key)
        row.update(delta=round(ca["score"] - cb["score"], 4), relation=rel,
                   wns_delta_ns=round(ca["wns"] - cb["wns"], 6) if ca["wns"] is not None and cb["wns"] is not None else None,
                   tns_delta_ns=round(ca["tns"] - cb["tns"], 4) if ca["tns"] is not None and cb["tns"] is not None else None)
        if "runtime_environment" in (ca.get("failure"), cb.get("failure")):
            strength = "runtime_environment"
        elif ca.get("valid") is False or ca.get("failure") or ca.get("status") not in ("succeeded", None):
            strength = "failed"
        elif rel == "identical":
            strength = "inert" if _timing_equal(ca, cb) else "timing_changed_same_labels"
        elif rel == "exchange":
            strength = "orientation"
        elif cb.get("measured_on") == "published" or ca.get("measured_on") == "published":
            strength = "published_reference"
        elif abs(row["delta"]) < tol[key[0]]["cell"]:
            strength = "within_sensitivity"
        else:
            strength = "measured"
        row["strength"] = strength
        rows.append(row)
    cases = []
    for case in ledger["cases"]:
        mine = [row for row in rows if row["case"] == case]
        scored = [row for row in mine if row["delta"] is not None]
        credible = [row for row in scored if row["strength"] in ("measured", "within_sensitivity")]
        mean = sum(row["delta"] for row in scored) / len(mine) if len(scored) == len(mine) else None
        cases.append({
            "case": case, "mean_delta": round(mean, 4) if mean is not None else None, "seeds": len(mine),
            "improved": sum(row["delta"] > SCORE_EPS for row in scored),
            "regressed": sum(row["delta"] < -SCORE_EPS for row in scored),
            "credible_improved": sum(row["delta"] > SCORE_EPS for row in credible),
            "orientation_cells": sum(row["strength"] == "orientation" for row in mine),
            "tolerance": tol[case]["case_mean"],
        })
    complete = a["complete"] and b["complete"]
    official = round(a["score"] - b["score"], 4) if complete else None
    per_case = {case: sum(1 for key in ledger["schedule"] if key[0] == case) for case in ledger["cases"]}
    weight = {case: 1.0 / (len(per_case) * count) for case, count in per_case.items()}
    positive = [row for row in rows if row["delta"] is not None and row["delta"] > SCORE_EPS]
    mass = sum(row["delta"] * weight[row["case"]] for row in positive)
    exchanged = sum(row["delta"] * weight[row["case"]] for row in positive if row["strength"] == "orientation")
    top = max(positive, key=lambda row: row["delta"] * weight[row["case"]], default=None)
    result = {
        "id": "%s-%s" % (a_id, b_id), "a": a_id, "b": b_id, "varies": varies,
        "exact": varies is not None and len(varies) == 1, "complete": complete, "official_delta": official,
        "cases": cases, "cells": rows,
        "orientation_share": round(exchanged / mass, 3) if mass > 0 else 0.0,
        "inert_cells": sum(row.get("strength") == "inert" for row in rows),
        "reference": ("published" if all(row.get("strength") == "published_reference" for row in rows if row["delta"] is not None)
                      else "mixed" if any(row.get("strength") == "published_reference" for row in rows) else "measured"),
    }
    if top is not None and official is not None and official > SCORE_EPS:
        result["top_cell"] = {"case": top["case"], "seed": top["seed"], "delta": top["delta"]}
        result["top_cell_share"] = round(top["delta"] * weight[top["case"]] / official, 3)
    return result


def case_supported(case_row):
    """A case gain that does not rest on one seed, an exchange, a published value or noise:
    the case mean clears its tolerance and most seeds improved on credible (unconfounded) cells."""
    return (case_row["mean_delta"] is not None and case_row["mean_delta"] >= case_row["tolerance"]
            and case_row["credible_improved"] * 2 > case_row["seeds"])


def credited_gain(result):
    """An official gain the next decision may build on, not only select."""
    return (result["official_delta"] is not None and result["official_delta"] > SCORE_EPS
            and result["orientation_share"] < ORIENTATION_SHARE
            and result.get("top_cell_share", 0.0) < NARROW_SHARE
            and any(case_supported(row) for row in result["cases"]))


def gain_reading(result):
    """One label for a contrast, used in prompts and decisions."""
    if result["official_delta"] is None:
        return "incomplete"
    if result["inert_cells"] * 2 > len(result["cells"]):
        return "labels_mostly_unchanged"
    if result["official_delta"] <= SCORE_EPS:
        return "no_gain"
    if result["orientation_share"] >= ORIENTATION_SHARE:
        return "orientation_carried"
    if result.get("top_cell_share", 0.0) >= NARROW_SHARE:
        return "one_cell"
    return "credited" if credited_gain(result) else "within_sensitivity"


# ----------------------------------------------------------------------------------------------
# Controls, squares, transplants and duplicates


def exact_contrasts(ledger, label, tol=None):
    """Every complete entry that differs from `label` in exactly one function, from anywhere in the run."""
    anchor = entry(ledger, label)
    found = []
    if not anchor["factors"] or not anchor["complete"]:
        return found
    for row in ledger["entries"]:
        if row["id"] == label or not row["complete"] or not row["factors"]:
            continue
        differs = [c for c in COMPONENTS if row["factors"][c] != anchor["factors"][c]]
        if len(differs) == 1:
            found.append(contrast(ledger, label, row["id"], tol))
    return found


def removal_controls(ledger, label):
    """For each function the anchor changed from the start or its parent: the program without that change."""
    anchor = entry(ledger, label)
    start = ledger["entries"][0]
    parent = ledger["by_id"].get(anchor.get("parent") or "")
    controls = []
    if not anchor["factors"]:
        return controls
    for component in COMPONENTS:
        for origin, reference in (("start", start), ("parent", parent)):
            if reference is None or not reference["factors"]:
                continue
            value = reference["factors"][component]
            if value == anchor["factors"][component]:
                continue
            factors = dict(anchor["factors"])
            factors[component] = value
            if any(row["factors"] == factors for row in controls):
                continue
            match = find_program(ledger, factors)
            controls.append({"component": component, "origin": origin, "factors": factors,
                             "status": "measured" if match else "missing",
                             "entry": match["id"] if match else None,
                             "donor": reference["id"]})
    return controls


def _square_orientation(ledger, programs):
    """Name the four programs of one square: P is the one nearest the start, AB shares no factor with P."""
    start = ledger["entries"][0]["factors"]
    order = {row["id"]: index for index, row in enumerate(ledger["entries"])}
    p = min(programs, key=lambda row: (-sum(row["factors"][c] == start[c] for c in COMPONENTS), order[row["id"]]))
    ab = next(row for row in programs if all(row["factors"][c] != p["factors"][c] for c in COMPONENTS))
    a = next(row for row in programs if row["factors"] == {"loss": ab["factors"]["loss"], "decoder": p["factors"]["decoder"]})
    b = next(row for row in programs if row["factors"] == {"loss": p["factors"]["loss"], "decoder": ab["factors"]["decoder"]})
    return {"P": p, "A": a, "B": b, "AB": ab}


def factorial_squares(ledger, tol=None):
    """Complete 2x2 squares P, A=(loss of AB, decoder of P), B=(loss of P, decoder of AB), AB, each once."""
    squares, found = [], set()
    complete = [row for row in ledger["entries"] if row["complete"] and row["factors"]]
    for ab in complete:
        for p in complete:
            if p is ab or any(p["factors"][c] == ab["factors"][c] for c in COMPONENTS):
                continue
            a = find_program(ledger, {"loss": ab["factors"]["loss"], "decoder": p["factors"]["decoder"]})
            b = find_program(ledger, {"loss": p["factors"]["loss"], "decoder": ab["factors"]["decoder"]})
            if not a or not b:
                continue
            programs = [find_program(ledger, row["factors"]) for row in (p, a, b, ab)]
            key = frozenset(tuple(sorted(row["factors"].items())) for row in programs)
            if key in found:
                continue
            found.add(key)
            arms = _square_orientation(ledger, programs)
            if any(arm["id"] == "S" and not arm["measured"] for arm in arms.values()):
                continue  # a published start is not a same-host arm
            cells = []
            for key in ledger["schedule"]:
                values = {name: arm["cells"][key]["score"] for name, arm in arms.items()}
                if any(value is None for value in values.values()):
                    cells.append({"case": key[0], "seed": key[1], "interaction": None})
                    continue
                cells.append({"case": key[0], "seed": key[1], **{name: round(v, 4) for name, v in values.items()},
                              "interaction": round(values["AB"] - values["A"] - values["B"] + values["P"], 4)})
            score = {name: arm["score"] for name, arm in arms.items()}
            interaction = score["AB"] - score["A"] - score["B"] + score["P"]
            best_single = max(("A", "B"), key=lambda name: score[name])
            if score["AB"] < score[best_single] - SCORE_EPS and interaction < -SCORE_EPS:
                verdict = "antagonistic"
            elif interaction > SCORE_EPS and score["AB"] > score[best_single]:
                verdict = "synergistic"
            else:
                verdict = "additive_within_tolerance" if abs(interaction) <= aggregate_tolerance(ledger, tol) else (
                    "subadditive" if interaction < 0 else "superadditive")
            squares.append({
                "arms": {name: arm["id"] for name, arm in arms.items()},
                "scores": {name: round(value, 4) for name, value in score.items()},
                "loss_effect": {"with_P_decoder": round(score["A"] - score["P"], 4),
                                "with_AB_decoder": round(score["AB"] - score["B"], 4)},
                "decoder_effect": {"with_P_loss": round(score["B"] - score["P"], 4),
                                   "with_AB_loss": round(score["AB"] - score["A"], 4)},
                "interaction": round(interaction, 4), "verdict": verdict, "cells": cells,
                "keep": max(("A", "B", "AB"), key=lambda name: score[name]),
            })
    return squares


def case_effects(ledger, tol=None):
    """Supported case-level gains of single-function changes, wherever they were measured in the run."""
    effects = []
    seen = set()
    complete = [row for row in ledger["entries"] if row["complete"] and row["factors"]]
    for a in complete:
        for b in complete:
            if a is b:
                continue
            differs = [c for c in COMPONENTS if a["factors"][c] != b["factors"][c]]
            if len(differs) != 1 or (b["id"], a["id"]) in seen:
                continue
            seen.add((a["id"], b["id"]))
            result = contrast(ledger, a["id"], b["id"], tol)
            component = differs[0]
            held = [c for c in COMPONENTS if c != component][0]
            for row in result["cases"]:
                credible = [cell for cell in result["cells"] if cell["case"] == row["case"]
                            and cell.get("strength") in ("measured", "within_sensitivity")]
                for better, worse, sign in ((a, b, 1), (b, a, -1)):
                    # The same contrast read in both directions: either side can be the improving program.
                    signed = {**row, "mean_delta": None if row["mean_delta"] is None else sign * row["mean_delta"],
                              "credible_improved": sum(sign * cell["delta"] > SCORE_EPS for cell in credible)}
                    if case_supported(signed):
                        effects.append({"component": component, "factor": better["factors"][component],
                                        "from": better["id"], "versus": worse["id"],
                                        "context": {held: better["factors"][held]}, "case": row["case"],
                                        "mean_delta": round(signed["mean_delta"], 4),
                                        "credible_seeds": signed["credible_improved"], "seeds": row["seeds"],
                                        "evidence": "%s-%s" % (better["id"], worse["id"])})
    return effects


def duplicate_of(ledger, label):
    """An earlier complete entry with the same labels (verified) or the same timing on every cell."""
    row = entry(ledger, label)
    if not row["complete"]:
        return None
    position = ledger["entries"].index(row)
    for earlier in ledger["entries"][1:position]:
        if not earlier["complete"]:
            continue
        cells = [(row["cells"][key], earlier["cells"][key]) for key in ledger["schedule"]]
        if all(a["labels"] and a["labels"] == b["labels"] for a, b in cells):
            return {"same_as": earlier["id"], "basis": "labels"}
        if all(_timing_equal(a, b) for a, b in cells):
            return {"same_as": earlier["id"], "basis": "timing_only"}
    return None
