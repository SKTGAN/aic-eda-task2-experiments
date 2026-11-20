"""Cross-round supervisor for the K1 search: one reversible adjustment after the second evaluation.

The review runs when the second complete official evaluation of a run has been recorded and before the
search policy's next step is used. It reads four records of this run together:

  1. the model requests the Agent actually sent  (search.jsonl `model_request` events),
  2. the model's recorded replies                (search.jsonl `model_response` events),
  3. every evaluated program against its parent   (unified diffs of the submitted sources),
  4. the official nine-cell receipts               (bridge replies plus organizer partition diagnostics).

It asks one question of the step the policy is about to take: does that step build on a candidate
whose gain the receipts do not attribute to the candidate's mechanism? This version has one rule for
that:

  A candidate qualifies when, on most cells, its final labels equal the official initial assignment
  or its exact inversion. The organizer diagnostic `partition_assignment_changed_fraction` measures
  this; "within MARGINAL_FRACTION of instances" counts as equal. A candidate also qualifies when its
  paired gain over its parent comes only from the inverted cells.

A qualifying candidate is not used as a parent for the next step. It stays eligible for final
selection. The search policy then chooses the next step without it, and the model is told why in one
request field, `supervisor_note`. The adjustment covers that one step only. After the next complete
evaluation, the unmodified policy resumes, and a `supervisor_check` event records whether the
adjustment produced an attributable comparison.

Everything the supervisor decides is written to search.jsonl before it takes effect and is reloaded on
restart, so a checkpoint is reviewed once. The supervisor makes no model call.
"""

import ast
import difflib
import hashlib
import json

from search_policy import COMPONENTS, MARGINAL_FRACTION, SAME_TIMING_NS, cell_key, function_keys

CHECKPOINTS = range(2, 10)
NOTE_FIELD = "supervisor_note"
DECISION_REASON = "supervisor_parent_excluded"
REPLY_LIMIT = 40000         # characters of each recorded model reply kept in the log
FALSIFIER_WORDS = ("invalidat", "falsif", "disprove")


def digest(value):
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


# ---------------------------------------------------------------- receipts: partitions and paired deltas

def assignment_rows(summary):
    """Per cell: changed fraction against the official initial assignment, inversion and residual change."""
    rows = []
    for cell in summary.get("cells") or []:
        change = cell.get("partition_change_vs_initial") or {}
        fraction = _number(change.get("partition_assignment_changed_fraction"))
        if fraction is None:
            fraction = _number((cell.get("metrics") or {}).get("partition_assignment_changed_fraction"))
        if fraction is None:
            rows.append({"cell": "/".join(cell_key(cell)), "changed_fraction": None})
            continue
        inverted = fraction > 0.5
        residual = 1.0 - fraction if inverted else fraction
        rows.append({"cell": "/".join(cell_key(cell)), "changed_fraction": fraction, "inverted": inverted,
                     "moved_after_undoing_inversion": residual,
                     "same_grouping": residual < MARGINAL_FRACTION})
    return rows


def paired_deltas(summary):
    comparison = summary.get("parent_comparison") or {}
    return {"/".join(cell_key(cell)): cell["score_delta"] for cell in comparison.get("cells") or []
            if _number(cell.get("score_delta")) is not None}


def parent_evidence(parent, archive, selection, checkpoint):
    """Separate the chosen parent's data from the policy's reason and other candidates' results."""
    observed = [entry for entry in archive if entry.get("status") == "succeeded"]
    result = {"reason": selection, "reviewed_receipts": checkpoint,
              "parent_basis": "this_run" if parent else "official_initial",
              "history": [{"candidate_id": row.get("candidate_id"), "score": row.get("score"),
                           "changes": (row.get("attempt") or {}).get("changed_components")}
                          for row in observed]}
    if not parent:
        return result
    result["official_score"] = parent.get("score")
    cells = [(c.get("score"), "/".join(cell_key(c))) for c in parent.get("cells", [])
             if _number(c.get("score")) is not None]
    if cells:
        result["highest_scoring_cell"] = max(cells)
        result["lowest_scoring_cell"] = min(cells)
    pairs = paired_deltas(parent)
    result["paired_reference"] = (parent.get("parent_comparison") or {}).get("parent_source")
    if len(pairs) == 9:
        best = max(pairs, key=pairs.get)
        result["strongest_gain"] = [best, pairs[best]]
        result["largest_regression"] = min(pairs.items(), key=lambda pair: pair[1])
        result["mean_delta_without_strongest"] = (sum(pairs.values()) - pairs[best]) / 8
    return result


def orientation_finding(summary):
    """Whether a candidate's paired gain comes only from inverting the official initial assignment."""
    rows = [row for row in assignment_rows(summary) if row.get("changed_fraction") is not None]
    deltas = paired_deltas(summary)
    comparison = summary.get("parent_comparison") or {}
    total = _number(comparison.get("official_score_delta"))
    same = [row for row in rows if row["same_grouping"]]
    inverted = [row["cell"] for row in same if row["inverted"]]
    from_inverted = sum(deltas.get(cell, 0.0) for cell in inverted)
    rest = sum(value for cell, value in deltas.items() if cell not in inverted)
    largest = max(deltas.items(), key=lambda item: item[1]) if deltas else None
    measured = bool(rows) and len(deltas) == len(rows) and comparison.get("complete") and total is not None
    return {
        "candidate_id": summary.get("candidate_id"), "request_id": summary.get("request_id"),
        "cells": len(rows), "same_grouping_cells": len(same), "inverted_same_grouping_cells": inverted,
        "points_from_inverted_cells": from_inverted, "points_from_other_cells": rest,
        "official_score_delta": total, "parent_source": comparison.get("parent_source"),
        "largest_cell": {"cell": largest[0], "score_delta": largest[1]} if largest else None,
        "qualifies": bool(measured and len(same) > len(rows) // 2 and inverted and total > 0 and rest <= 0),
    }


def host_finding(summary):
    """Cells whose labels equal the official initial assignment yet whose timing differs from the reference."""
    comparison = summary.get("parent_comparison") or {}
    if comparison.get("parent_source") != "published_initial_reference":
        return []
    identical = {row["cell"] for row in assignment_rows(summary) if row.get("changed_fraction") == 0}
    found = []
    for cell in comparison.get("cells") or []:
        name = "/".join(cell_key(cell))
        drift = [abs(cell.get(metric) or 0.0) for metric in ("wns_slack_delta_ns", "tns_slack_delta_ns")]
        if name in identical and max(drift) >= SAME_TIMING_NS:
            found.append({"cell": name, "score_delta": cell.get("score_delta"),
                          "wns_slack_delta_ns": cell.get("wns_slack_delta_ns"),
                          "tns_slack_delta_ns": cell.get("tns_slack_delta_ns")})
    return found


def loss_size_finding(results, sources, initial):
    """Size of an added loss term, read from tp_gnn_final_loss against a run that kept the loss unchanged.

    The control is an evaluated program of this run whose loss function equals the loss edit's parent
    loss. Here that is the official loss; training is deterministic per cell, so the difference
    on matched cells is the added term at the end of training.
    """
    initial_loss = function_keys(initial)[0]
    by_loss = {}
    for result in results:
        source = sources.get(result["request_id"])
        if source and result.get("status") == "succeeded":
            by_loss.setdefault(function_keys(source)[0], []).append(result)
    controls = by_loss.get(initial_loss) or []
    findings = []
    for key, edited in by_loss.items():
        if key == initial_loss or not controls:
            continue
        for result in edited:
            losses = {}
            for name, run in (("edit", result), ("control", controls[0])):
                for cell in run["feedback"]["cells"]:
                    value = _number((cell.get("metrics") or {}).get("tp_gnn_final_loss"))
                    if value is not None:
                        losses.setdefault("/".join(cell_key(cell)), {})[name] = value
            pairs = [(row["edit"] - row["control"], row["control"]) for row in losses.values()
                     if "edit" in row and "control" in row]
            if not pairs or len(pairs) != len(result["feedback"]["cells"]):
                continue
            changes = [delta for delta, _ in pairs]
            shares = [delta / base for delta, base in pairs if base]
            findings.append({"candidate_id": result["candidate_id"], "control_candidate_id": controls[0]["candidate_id"],
                             "cells": len(pairs), "loss_change_min": min(changes), "loss_change_max": max(changes),
                             "loss_share_min": min(shares), "loss_share_max": max(shares)})
    return findings


# ---------------------------------------------------------------- requests, replies and diffs

def stated_falsifiers(source):
    """Sentences of each docstring that state how the hypothesis would fail, quoted as written."""
    quoted = {}
    try:
        functions = ast.parse(source).body
    except SyntaxError:
        return quoted
    for name, function in zip(COMPONENTS, functions):
        text = " ".join((ast.get_docstring(function) or "").split())
        sentences = [part.strip() for part in text.replace("; ", ". ").split(". ")]
        hits = [sentence for sentence in sentences if any(word in sentence.lower() for word in FALSIFIER_WORDS)]
        if hits:
            quoted[name] = " ".join(hits)[:400]
    return quoted


def request_digest(events):
    """Which inputs each recorded model request carried, without repeating the payloads."""
    rows = []
    for event in events:
        if event.get("event") != "model_request":
            continue
        request = event.get("request") or {}
        rows.append({"call": event.get("call"), "role": event.get("role"),
                     "search_intent": request.get("search_intent"),
                     "decision_reason": (request.get("decision") or {}).get("reason"),
                     "fields": sorted(request), "null_fields": sorted(key for key, value in request.items() if value is None),
                     "expert_section": event.get("expert_section"), "system_sha256": event.get("system_sha256"),
                     "request_sha256": digest(request)})
    return rows


def reply_digest(events):
    return [{"call": event.get("call"), "role": event.get("role"), "characters": len(event.get("text") or ""),
             "text_sha256": digest(event.get("text") or "")}
            for event in events if event.get("event") == "model_response"]


def program_diffs(results, sources, attempts, initial, baseline_id):
    """Unified diff of every evaluated program against the program it was built from."""
    by_candidate = {baseline_id: initial}
    for result in results:
        if sources.get(result["request_id"]):
            by_candidate[result["candidate_id"]] = sources[result["request_id"]]
    rows = []
    for result in results:
        source = sources.get(result["request_id"])
        parent_id = (attempts.get(result["request_id"]) or {}).get("parent_id")
        parent = by_candidate.get(parent_id)
        if not source or parent is None:
            rows.append({"candidate_id": result["candidate_id"], "parent_id": parent_id, "diff": None})
            continue
        diff = "".join(difflib.unified_diff(parent.splitlines(True), source.splitlines(True),
                                            "parent/" + str(parent_id)[:12], "candidate/" + result["candidate_id"][:12]))
        rows.append({"candidate_id": result["candidate_id"], "parent_id": parent_id,
                     "parent_sha256": digest(parent), "candidate_sha256": digest(source),
                     "changed_lines": sum(line[:1] in "+-" and line[:3] not in ("+++", "---")
                                          for line in diff.splitlines()),
                     "falsifiers": stated_falsifiers(source), "diff": diff})
    return rows


# ---------------------------------------------------------------- the review and its record

def dossier(checkpoint, step, archive, results, sources, attempts, initial, baseline_id, events):
    """Everything the review reads, in one structure that is saved next to search.jsonl."""
    return {
        "checkpoint": checkpoint,
        "policy_step": step,
        "requests": request_digest(events),
        "replies": reply_digest(events),
        "programs": program_diffs(results, sources, attempts, initial, baseline_id),
        "receipts": archive,
        "orientation": [orientation_finding(summary) for summary in archive],
        "identical_labels_with_timing_change": {summary["candidate_id"]: host_finding(summary) for summary in archive},
        "loss_size": loss_size_finding(results, sources, initial),
    }


def builds_on(step, archive):
    """The archive row of the candidate the policy step builds on, or None."""
    if step.get("action") not in ("propose", "recombine") or not step.get("parent"):
        return None
    return next((summary for summary in archive if summary["request_id"] == step["parent"]), None)


def review(checkpoint, step, folder_dossier):
    """Decide keep or exclude_parent for the next step. Pure function of the dossier."""
    target = builds_on(step, folder_dossier["receipts"])
    finding = orientation_finding(target) if target else None
    decision = {"checkpoint": checkpoint, "policy_step": step, "rule": "orientation_only_gain",
                "applies_to": "the next step only; final selection unchanged"}
    if not finding or not finding["qualifies"]:
        decision.update(action="keep", basis=finding)
        return decision
    decision.update(action="exclude_parent", candidate_id=finding["candidate_id"],
                    request_id=finding["request_id"], basis=finding)
    decision["note"] = note_text(checkpoint, finding, folder_dossier)
    decision["predictions"] = {
        "adoption": "the next request's parent is not the excluded candidate and it carries the note",
        "attributable": "the next complete evaluation changes the grouping (beyond an inversion) on most cells",
        "score": "no direction predicted; the excluded candidate stays eligible for final selection",
    }
    decision["withdraw_if"] = ("the next complete evaluation again keeps the grouping on most cells; the "
                               "adjustment then bought no attributable comparison and is not repeated")
    return decision


def note_text(checkpoint, finding, folder_dossier):
    other = finding["cells"] - len(finding["inverted_same_grouping_cells"])
    largest = finding["largest_cell"]
    receipt = next(summary for summary in folder_dossier["receipts"] if summary["candidate_id"] == finding["candidate_id"])
    lines = [
        "Cross-round review after {} official evaluations of this run (this run's receipts only). Candidate {} "
        "(official score {:.2f}, {:+.2f} against its parent) is not the parent for this step; it stays eligible "
        "for final selection.".format(checkpoint, finding["candidate_id"], receipt.get("score") or 0.0,
                                      finding["official_score_delta"]),
        "On {} of {} cells its final labels equal the official initial assignment or its exact inversion within "
        "{:g}% of instances (partition_assignment_changed_fraction). The {} inverted cells ({}) account for {:+.2f} "
        "summed cell points against its parent and the other {} cells for {:+.2f}. Its largest cell is {} at "
        "{:+.2f}. Its gain therefore comes from inverting the initial assignment on those cells, not from a "
        "different grouping.".format(
            finding["same_grouping_cells"], finding["cells"], 100 * MARGINAL_FRACTION,
            len(finding["inverted_same_grouping_cells"]), ", ".join(finding["inverted_same_grouping_cells"]),
            finding["points_from_inverted_cells"], other, finding["points_from_other_cells"],
            largest["cell"], largest["score_delta"]),
    ]
    for size in folder_dossier.get("loss_size") or []:
        edited = next((summary for summary in folder_dossier["receipts"] if summary["candidate_id"] == size["candidate_id"]), None)
        identical = sum(row.get("changed_fraction") == 0 for row in assignment_rows(edited)) if edited else None
        lines.append(
            "Loss edit {} raised tp_gnn_final_loss by {:.3f} to {:.3f} on every cell against {}, which kept that "
            "loss unchanged ({:.2f}% to {:.2f}% of the loss); {} of {} of its assignments were identical to the "
            "official initial assignment.".format(
                size["candidate_id"], size["loss_change_min"], size["loss_change_max"], size["control_candidate_id"],
                100 * size["loss_share_min"], 100 * size["loss_share_max"], identical, size["cells"]))
    lines.append("In the docstring of each function you change, predict the share of instances whose die changes "
                 "relative to the official initial assignment once a whole-assignment inversion is undone.")
    return " ".join(lines)


def check(decision, summary, request_logged):
    """After the next complete evaluation: did the adjustment happen, and is the new comparison attributable?"""
    rows = [row for row in assignment_rows(summary) if row.get("changed_fraction") is not None]
    regrouped = sum(not row["same_grouping"] for row in rows)
    comparison = summary.get("parent_comparison") or {}
    deltas = paired_deltas(summary)
    attributable = bool(rows) and regrouped > len(rows) // 2
    return {
        "checkpoint": decision["checkpoint"], "excluded_candidate_id": decision["candidate_id"],
        "evaluated_candidate_id": summary.get("candidate_id"),
        "adopted": bool(request_logged) and (summary.get("attempt") or {}).get("parent_id") != decision["candidate_id"],
        "cells_with_new_grouping": regrouped, "cells": len(rows),
        "inverted_cells": sum(row["inverted"] for row in rows),
        "official_score": summary.get("score"),
        "official_score_delta_vs_parent": comparison.get("official_score_delta"),
        "parent_source": comparison.get("parent_source"),
        "largest_cell_gain": max(deltas.items(), key=lambda item: item[1]) if deltas else None,
        "largest_cell_loss": min(deltas.items(), key=lambda item: item[1]) if deltas else None,
        "attributable_comparison": attributable,
        "withdraw": not attributable,
    }
