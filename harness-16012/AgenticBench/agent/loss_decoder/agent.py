"""Search the task-2 loss and decoder through the metered contest bridge."""

import ast
import hashlib
import json
from math import isclose, isfinite
from pathlib import Path
from statistics import mean
import time
import traceback
from uuid import uuid4

from candidate_reply import generated_program, model_text
from cpu_checks import CPUChecks
from experiment_evidence import experiment_record
from contest2.agent_api import AgentAPIError
from contest2.model_pricing import MODEL_ID
from contest2.scoring import reference_table, score_metrics
from local_tasks.tp_gnn_local_task_definitions import DECODER_TASK, validate_program
from paired_feedback import (REPAIR_CHAIN, assignment_difference, assignment_snapshot, comparison_for_prompt,
                             compare_feedback, failure_evidence, load_attempts, published_partition_changes,
                             related_experiment)


EXPERIENCE_HEADING = "## Offline Expert Knowledge"
UNCHANGED_FUNCTION = {"loss_only": 1, "decoder_only": 0}
# The loss control goes first: it is the opening trial that moves the partition on every cell.
# A decoder control that reproduces the start grouping measures die orientation and this host.
OPENING = ("loss_only", "decoder_only")
OPENING_TRIALS = 3
SWAP_FRACTION = 0.5          # more than half of the instances changed: the start grouping with dies exchanged
KEPT_UP_TO_SWAP = 1e-4       # changed-instance fraction, after undoing a die exchange, still counted as the start grouping
SINGLE_CELL_SHARE = 0.75     # a gain is narrow when one case/seed cell carries this share of it
REPLAN_AFTER_INVALID = 3     # consecutive rejected programs before the cached plan is discarded
STOP_AFTER_INVALID = 6       # consecutive rejected programs before search stops with a scored candidate
STOP_WITHOUT_CANDIDATE = 12
BRIDGE_ATTEMPTS = 6
ROBUST_MIN_CASES = 2         # final selection: cases, and seeds, whose mean gain over the start must be positive
ABLATION_LIMIT = 2
ABLATION_MARGIN = 2.0
ABLATION_LOSS_SHARE = 0.65
CONTAINER_PYTHON = (3, 8)    # the agent and evaluator image runs Python 3.8
PLAN_TASK = """Return a short experiment plan, not code. Use at most 90 words.
State the exact parent decision to change, one plausible mechanism that reaches the legal labels,
the measured evidence (or why evidence is missing), the expected WNS or TNS effect, and a falsifier.
For an opening probe, identify the signal, the official decision it changes and how to tell whether
repair erased the effect. For a follow-up, give one factor and matching evidence about timing and
legal labels where available. Name gains the next trial should keep and the observation that would
falsify the proposal. Treat timing changes with unchanged labels as confounded.
Use only the published interface. Do not key the algorithm to case or seed identities.
Field notes. `start_reference` counts start cells measured on this run's host; the others are published
values from another host. `die_swap_vs_initial` marks a cell holding the start grouping with dies exchanged.
`decision.reason` classifies the latest paired comparison: `broad_gain`, `narrow_gain` (one cell or one
case carries it), `orientation_only` and `partition_mostly_unchanged` (start grouping kept, dies possibly
exchanged), `broad_regression`, `duplicate_outcome` (every cell repeats an earlier candidate's labels and
timing). For an added loss term, the change in `tp_gnn_final_loss` from the parent approximates the term's
size. Per cell, `raw_cut_net_count_delta` and `balanced_cut_net_count_delta` show what the decoder changed
before repair; `feasible_cut_net_count_delta` and `assignment_vs_parent` show what reached the legal labels.
A raw change with no feasible change was undone by repair."""
OPENING_TASK = """When decision.opening_trial is present, use the initial program as the common
control. Change only the requested component. The opening entries in prior_trials name the
mechanisms already tried. Change a different numerical decision in the same component on its
second visit. Retuning coefficients, renaming locals or changing only die orientation does not
constitute a new mechanism. Propose a measurable effect on the legal partition and timing."""
ABLATION_TASK = """When decision.ablation is present, use the supplied candidate as the control for a
one-factor experiment. Change one mechanism in the named component, or choose one component if none is specified. Leave other
behavior intact. State the factor, what should improve on the target cell, and why the protected
cells should retain their gains. Use case and seed names only to explain the measurements. The
algorithm must apply the same rule to every input. Each trial is compared directly with this
control on the full training schedule."""
TIMING_KEYS = {
    "final_global_wns_setup_ns", "final_global_tns_setup_ns", "cut_net_count", "timing_weighted_cut",
    "wns_deficit_improvement", "tns_deficit_improvement", "tp_gnn_repair_moved_area_fraction",
    "tp_gnn_positive_pair_cosine_median", "tp_gnn_negative_pair_cosine_median",
    "tp_gnn_embedding_total_variance", "tp_gnn_final_loss", *REPAIR_CHAIN,
}


def compact_feedback(row):
    if not row:
        return row
    copy = dict(row)
    copy["cells"] = [
        {**cell, "metrics": {key: value for key, value in (cell.get("metrics") or {}).items()
                             if key in TIMING_KEYS}}
        for cell in row["cells"]
    ]
    return copy


def function_keys(source, compare_structure=False):
    functions = ast.parse(source).body
    for function in functions:
        if ast.get_docstring(function, clean=False) is not None:
            function.body.pop(0)
        if compare_structure:
            nodes = list(ast.walk(function))
            assigned = {node.id for node in nodes if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
            selectors = {id(index) for node in nodes if isinstance(node, ast.Subscript)
                         for index in ast.walk(node.slice) if isinstance(index, ast.Constant)}
            names = {}
            for node in nodes:
                if isinstance(node, ast.Constant) and type(node.value) in (int, float) and id(node) not in selectors:
                    node.value = 0
                elif isinstance(node, ast.Name) and node.id in assigned:
                    node.id = names.setdefault(node.id, f"__local_{len(names)}")
    return tuple(ast.dump(function, include_attributes=False) for function in functions)


def ask_model(context, instructions, request, effort="low", purpose="generation"):
    payload = {
        "model": MODEL_ID,
        "stream": False,
        "reasoning": {"effort": effort},
        "input": [
            {"type": "message", "role": "system", "content": instructions},
            {"type": "message", "role": "user", "content": json.dumps(request, ensure_ascii=False)},
        ],
    }
    folder = Path(__file__).resolve().parent
    call_id = uuid4().hex
    write_event(folder, "model_request", call_id=call_id, purpose=purpose, payload=payload)
    try:
        response = context.model.responses_create(payload)
    except AgentAPIError:
        write_event(folder, "model_response", call_id=call_id, purpose=purpose, status="gateway_error")
        raise
    fields = {"status": "invalid_response"}
    if isinstance(response, dict):
        fields["status"] = response.get("status")
        usage = response.get("usage")
        if isinstance(usage, dict):
            fields["usage"] = {key: usage[key] for key in ("input_tokens", "output_tokens") if key in usage}
        try:
            fields["output_text"] = model_text(response)
        except ValueError as error:
            fields["issue"] = str(error)
    write_event(folder, "model_response", call_id=call_id, purpose=purpose, **fields)
    return response


def shortened(request):
    """A smaller request for a retry after an over-long or empty reply."""
    keep = ("search_intent", "decision", "parent_id", "parent_program", "evaluations_remaining",
            "previous_generation_issue", "start_reference", "experiment_plan", "largest_regression",
            "experiment_record")
    smaller = {key: request[key] for key in keep if key in request}
    smaller["prior_trials"] = (request.get("prior_trials") or [])[-3:]
    return smaller


def proposal_keys(source, parent_key, unchanged, seen):
    key = function_keys(source)
    if key in seen:
        raise ValueError("The response repeats an already considered program")
    if unchanged is not None and key[unchanged] != parent_key[unchanged]:
        raise ValueError("Keep the other function unchanged for this paired search direction")
    return key


def candidate_gate(source):
    """Cheap check before a two-hour evaluation: the program must parse as Python 3.8, the container's
    version. Raises ValueError, which returns the reason to the model as a generation issue."""
    try:
        ast.parse(source, feature_version=CONTAINER_PYTHON)
    except SyntaxError as error:
        raise ValueError("The program uses syntax newer than Python 3.8: %s" % error.msg)


def outcome_fingerprint(result):
    """Per-cell labels-and-timing identity: equal fingerprints mean equal official outcomes."""
    if result["status"] != "succeeded":
        return None
    rows = []
    for cell in result["feedback"]["cells"]:
        metrics = cell.get("metrics") or {}
        values = (metrics.get("partition_assignment_changed_count"), metrics.get("cut_net_count"),
                  metrics.get("final_global_wns_setup_ns"), metrics.get("final_global_tns_setup_ns"))
        if any(not isinstance(value, (int, float)) for value in values):
            return None
        rows.append((cell["case"], str(cell["seed"]), values[0], values[1], round(values[2], 9), round(values[3], 6)))
    return tuple(sorted(rows)) or None


def robust_gain(result, start):
    """Gain over the start reference with the single best cell removed, and how widely it is spread."""
    if result["status"] != "succeeded" or start is None:
        return None
    base = {(cell["case"], str(cell["seed"])): cell.get("score") for cell in start["feedback"]["cells"]}
    deltas = {}
    for cell in result["feedback"]["cells"]:
        key = cell["case"], str(cell["seed"])
        if not isinstance(cell.get("score"), (int, float)) or not isinstance(base.get(key), (int, float)):
            return None
        deltas[key] = cell["score"] - base[key]
    if set(deltas) != set(base):
        return None

    def aggregate(values):  # the official mean over cases of the seed mean
        cases = sorted({case for case, _ in values})
        return mean(mean(value for (case, _), value in values.items() if case == name) for name in cases)

    top = max(deltas, key=deltas.get)
    without_top = {**deltas, top: min(0.0, deltas[top])}
    cases = sorted({case for case, _ in deltas})
    seeds = sorted({seed for _, seed in deltas})
    cases_up = sum(mean(value for (case, _), value in deltas.items() if case == name) > 0 for name in cases)
    seeds_up = sum(mean(value for (_, seed), value in deltas.items() if seed == name) > 0 for name in seeds)
    loo = aggregate(without_top)
    return {"gain": aggregate(deltas), "gain_without_best_cell": loo,
            "best_cell": {"case": top[0], "seed": top[1], "score_delta": deltas[top]},
            "improved_cases": cases_up, "cases": len(cases), "improved_seeds": seeds_up, "seeds": len(seeds),
            "eligible": (loo > 0 and cases_up >= min(ROBUST_MIN_CASES, len(cases))
                         and seeds_up >= min(ROBUST_MIN_CASES, len(seeds)))}


def select_final(history, start, best):
    """Return the official training incumbent; retain sensitivity diagnostics for review."""
    summary = []
    for result in history:
        stats = robust_gain(result, start)
        if stats is not None:
            summary.append({"candidate_id": result["candidate_id"], "score": result["feedback"]["score"], **stats})
    return best, {"rule": "highest_official_score", "candidates": summary}


def score_key(result):
    feedback = result["feedback"]
    cells = feedback["cells"]
    tns = [cell.get("metrics", {}).get("tns_deficit_improvement") for cell in cells]
    complete_tns = bool(tns) and all(value is not None for value in tns)
    return feedback["score"], mean(tns) if complete_tns else float("-inf")


def inert_evidence(feedback):
    comparison = feedback.get("parent_comparison") or {}
    score_delta = comparison.get("official_score_delta")
    if not comparison.get("complete") or comparison.get("candidate_invalid_cells"):
        return None

    # Against the start, the organizer's assignment diagnostic is exact. Keeping the start grouping,
    # with or without exchanging the dies, says nothing about the edited mechanism, whatever the score did.
    partition = feedback.get("partition_changes_vs_initial", {})
    identical = partition.get("identical_assignments", 0)
    kept = partition.get("kept_up_to_swap", identical)
    if (comparison.get("parent_source") == "published_initial_reference"
            and kept > comparison["expected_cells"] // 2):
        reason = "orientation_only" if partition.get("die_swaps") else "partition_mostly_unchanged"
        return {"reason": reason, "identical_assignments": identical, "kept_up_to_swap": kept,
                "die_swaps": partition.get("die_swaps", 0)}
    if score_delta is None or score_delta > 0:
        return None

    unchanged = sum(
        all(cell.get(metric) is not None and abs(cell[metric]) < 1e-6
            for metric in ("wns_slack_delta_ns", "tns_slack_delta_ns"))
        for cell in comparison["cells"]
    )
    if unchanged > comparison["expected_cells"] // 2:
        return {"reason": "timing_mostly_unchanged", "unchanged_pairs": unchanged}
    return None


def case_deltas(comparison):
    """Mean paired score change per case, from the case rows or, failing that, the cells."""
    rows = {row["case"]: row.get("mean_paired_score_delta") for row in comparison.get("cases") or []}
    if not rows:
        cells = {}
        for cell in comparison.get("cells", []):
            if isinstance(cell.get("score_delta"), (int, float)):
                cells.setdefault(cell["case"], []).append(cell["score_delta"])
        rows = {case: mean(values) for case, values in cells.items()}
    return {case: value for case, value in rows.items() if isinstance(value, (int, float))}


def seed_tradeoffs(feedback):
    """Find opposite, material score changes inside one design, regardless of its mean."""
    paired = feedback.get("parent_comparison") or {}
    if (not paired.get("complete") or paired.get("candidate_invalid_cells") or feedback.get("duplicate_of")
            or feedback.get("status", "succeeded") != "succeeded"):
        return []
    by_case = {}
    for row in paired.get("cells", []):
        delta = row.get("score_delta")
        if "seed" not in row or not isinstance(delta, (float, int)) or not isfinite(delta):
            return []
        by_case.setdefault(row["case"], []).append(row)
    fields = ("case", "seed", "score_delta", "wns_slack_delta_ns", "tns_slack_delta_ns",
              "wns_deficit_improvement_delta", "tns_deficit_improvement_delta", "assignment_vs_parent")
    initial_counts = {(cell["case"], str(cell["seed"])): (cell.get("partition_change_vs_initial") or {}).get(
        "partition_assignment_changed_count") for cell in feedback.get("cells", [])}
    splits = []
    for case, rows in by_case.items():
        gains = [row for row in rows if row["score_delta"] >= ABLATION_MARGIN]
        losses = [row for row in rows if row["score_delta"] <= -ABLATION_MARGIN]
        if gains and losses:
            # Equal and opposite changes disappear completely when averaged. Rank by the
            # magnitude of the smaller opposing total, in mean-score points for this design.
            cancelled = min(sum(row["score_delta"] for row in gains), -sum(row["score_delta"] for row in losses))
            seeds = []
            for row in rows:
                observed = {key: row[key] for key in fields if key in row}
                changed = (row.get("assignment_vs_parent") or {}).get("changed_count")
                if paired.get("parent_source") == "published_initial_reference":
                    changed = initial_counts.get((case, str(row["seed"])), changed)
                if changed == 0 and abs(row["score_delta"]) >= ABLATION_MARGIN:
                    observed["timing_shift_with_unchanged_labels"] = True
                seeds.append(observed)
            splits.append({"case": case, "mean_delta": mean(row["score_delta"] for row in rows),
                           "offset_points_per_seed": cancelled / len(rows), "seeds": seeds})
    return sorted(splits, key=lambda s: (-s["offset_points_per_seed"], s["case"]))


def trial_evidence(feedback):
    """What a complete paired comparison says about the edited mechanism; None when unverified."""
    comparison = feedback.get("parent_comparison") or {}
    if feedback.get("duplicate_of"):
        return {"reason": "duplicate_outcome", "same_as": feedback["duplicate_of"]}
    delta = comparison.get("official_score_delta")
    if delta is None or not comparison.get("complete") or comparison.get("candidate_invalid_cells"):
        return None
    splits = seed_tradeoffs(feedback)
    if splits:
        return {"reason": "opposing_seed_changes", "cases_with_tradeoff": splits}
    inert = inert_evidence(feedback)
    if inert:
        return inert
    cases = case_deltas(comparison)
    per_case = {}
    for cell in comparison.get("cells", []):
        per_case[cell["case"]] = per_case.get(cell["case"], 0) + 1
    scored = [cell for cell in comparison.get("cells", []) if isinstance(cell.get("score_delta"), (int, float))]
    summary = {"improved_cases": sum(value > 0 for value in cases.values()),
               "regressed_cases": sum(value < 0 for value in cases.values()), "cases": len(cases)}
    if delta > 0 and scored:
        # Official aggregate: mean over cases of the seed mean, so one cell weighs 1 / (cases * seeds).
        top = max(scored, key=lambda cell: cell["score_delta"])
        share = top["score_delta"] / (len(per_case) * per_case[top["case"]]) / delta
        summary["largest_cell"] = {key: top.get(key) for key in ("case", "seed", "score_delta")}
        summary["largest_cell_share"] = round(share, 3)
        narrow = share >= SINGLE_CELL_SHARE or 2 * summary["improved_cases"] <= len(cases)
        return {"reason": "narrow_gain" if narrow else "broad_gain", **summary}
    if delta < 0 and 2 * summary["regressed_cases"] > len(cases):
        return {"reason": "broad_regression", **summary}
    return None


def summarize_trial(feedback):
    attempt = feedback.get("attempt") or {}
    comparison = feedback.get("parent_comparison") or {}
    return {
        "candidate_id": feedback["candidate_id"],
        "parent_id": attempt.get("parent_id"),
        "changed_components": attempt.get("changed_components", {}),
        "status": feedback["status"],
        "score": feedback["score"],
        "paired_score_delta": comparison.get("official_score_delta"),
        "evidence": trial_evidence(feedback),
        "ablation_result": feedback.get("ablation_result"),
        "opening_trial": attempt.get("opening_trial"),
        "component_donor": attempt.get("component_donor"),
        "donor_pair": feedback.get("donor_pair"),
    }


def design_ablation(archive):
    """Schedule a one-factor follow-up using the last fully measured candidate as the control."""
    latest = archive[-1]
    attempt = latest.get("attempt") or {}
    components = tuple(attempt.get("changed_components", {}))
    used = [row for row in archive if (row.get("attempt") or {}).get("ablation")]
    paired = latest.get("parent_comparison") or {}
    evidence = trial_evidence(latest) or {}
    if (len(used) >= ABLATION_LIMIT or attempt.get("ablation") or len(components) != 1
            or components[0] not in ("loss", "decoder") or latest.get("status") != "succeeded"
            or latest.get("duplicate_of") or not paired.get("complete")
            or paired.get("candidate_invalid_cells")):
        return None

    rows = paired.get("cells", [])
    gains = [row for row in rows if row["score_delta"] >= ABLATION_MARGIN]
    losses = [row for row in rows if row["score_delta"] <= -ABLATION_MARGIN]
    total_loss = sum(-row["score_delta"] for row in rows if row["score_delta"] < 0)
    worst_loss = max((-row["score_delta"] for row in losses), default=0)
    opening_loss = (len(archive) == 1 and not attempt.get("opening_trial") and components == ("loss",)
                    and evidence.get("reason") in ("partition_mostly_unchanged", "timing_mostly_unchanged"))
    measured_tradeoff = (paired.get("parent_source") == "run_evaluation" and len(gains) >= 2
                         and worst_loss > 0 and worst_loss >= ABLATION_LOSS_SHARE * total_loss
                         and evidence.get("reason") not in ("narrow_gain", "orientation_only"))
    if not (opening_loss or measured_tradeoff):
        return None

    # When the reference mixes hosts, identical assignments are not evidence of an algorithm effect.
    unchanged = {(cell["case"], cell["seed"]) for cell in latest.get("cells", [])
                 if cell.get("partition_change_vs_initial", {}).get("partition_assignment_changed_count") == 0}
    if paired.get("parent_source") == "published_initial_reference":
        gains = [row for row in gains if (row["case"], row["seed"]) not in unchanged]
        losses = [row for row in losses if (row["case"], row["seed"]) not in unchanged]
    fields = ("case", "seed", "score_delta", "wns_slack_delta_ns", "tns_slack_delta_ns",
              "raw_cut_net_count_delta", "balanced_cut_net_count_delta", "feasible_cut_net_count_delta",
              "assignment_vs_parent")
    target = min(losses, key=lambda row: row["score_delta"], default=None)
    return {
        "reason": "test_opening_loss" if opening_loss else "repair_tradeoff",
        "component": components[0],
        "ablation": {
            "diagnosis_reference": paired.get("parent_source"),
            "target": {key: target[key] for key in fields if key in target} if target else None,
            "protected_cells": [{key: row[key] for key in fields if key in row} for row in gains],
            "minimum_target_gain": ABLATION_MARGIN,
            "maximum_protected_loss": ABLATION_MARGIN,
            "maximum_case_mean_loss": ABLATION_MARGIN,
        },
    }


def seed_followup(history, archive):
    """Spend an existing follow-up slot on a measured design/seed tradeoff, including an older branch."""
    plans = [s["attempt"] for s in archive if (s.get("attempt") or {}).get("ablation")]
    if len(plans) >= ABLATION_LIMIT:
        return None
    tried = {(a.get("parent_id"), (a["ablation"].get("target") or {}).get("case")) for a in plans}
    options = []
    for pos, (result, summary) in enumerate(zip(history, archive)):
        if not result.get("source") or (summary.get("ablation_result") or {}).get("status") in ("failed", "unverified"):
            continue
        for split in seed_tradeoffs(summary):
            usable = [cell for cell in split["seeds"] if not cell.get("timing_shift_with_unchanged_labels")]
            gains = [cell for cell in usable if cell["score_delta"] >= ABLATION_MARGIN]
            losses = [cell for cell in usable if cell["score_delta"] <= -ABLATION_MARGIN]
            if gains and losses and (result["candidate_id"], split["case"]) not in tried:
                mass = min(sum(c["score_delta"] for c in gains), -sum(c["score_delta"] for c in losses))
                options.append((mass / len(split["seeds"]), pos, result, summary, split, gains, losses))
    if not options:
        return None
    _, _, control, summary, split, protected, losses = max(options, key=lambda item: item[:2])
    target = min(losses, key=lambda cell: cell["score_delta"])
    decision = {"reason": "repair_within_case_seed_tradeoff", "seed_comparison": split,
                "ablation": {"diagnosis_reference": summary["parent_comparison"].get("parent_source"),
                             "target": target, "protected_cells": protected, "minimum_target_gain": ABLATION_MARGIN,
                             "maximum_protected_loss": ABLATION_MARGIN, "maximum_case_mean_loss": ABLATION_MARGIN,
                             "maximum_other_seed_loss": ABLATION_MARGIN}}
    components = tuple((summary.get("attempt") or {}).get("changed_components", {}))
    if len(components) == 1 and components[0] in ("loss", "decoder"):
        decision["component"] = components[0]
    return control, "repair", decision


def assess_ablation(plan, paired):
    """Judge a trial against its measured control, using the same seeds for every check."""
    if (not paired or not paired.get("complete") or paired.get("candidate_invalid_cells")
            or paired.get("parent_source") != "run_evaluation" or paired.get("official_score_delta") is None):
        return {"status": "unverified"}
    values = {(row["case"], row["seed"]): row["score_delta"] for row in paired["cells"]}
    protected = [(row["case"], row["seed"]) for row in plan["protected_cells"]]
    target = plan["target"]
    target_key = (target["case"], target["seed"]) if target else None
    required = protected + ([target_key] if target_key else [])
    if any(key not in values for key in required):
        return {"status": "unverified"}
    target_gain = values[target_key] if target_key else max(values.values())
    lost = [{"case": c, "seed": s, "score_delta": values[c, s]} for c, s in protected
            if values[c, s] < -plan["maximum_protected_loss"]]
    case_losses = {case: delta for case, delta in case_deltas(paired).items()
                   if delta < -plan["maximum_case_mean_loss"]}
    seed_limit = plan.get("maximum_other_seed_loss")
    seed_losses = [{"case": case, "seed": seed, "score_delta": delta} for (case, seed), delta in values.items()
                   if seed_limit is not None and (case, seed) != target_key and delta < -seed_limit]
    score_delta = paired["official_score_delta"]
    accepted = (target_gain >= plan["minimum_target_gain"] and not lost
                and not case_losses and not seed_losses and score_delta >= 0)
    return {"status": "passed" if accepted else "failed", "target_gain": target_gain,
            "protected_losses": lost, "other_seed_losses": seed_losses, "case_mean_losses": case_losses,
            "score_delta": score_delta}


def opening_probe(archive, opening):
    if len(archive) >= OPENING_TRIALS or not all(
            (row.get("attempt") or {}).get("opening_trial") for row in archive):
        return None
    index = len({row["attempt"]["opening_trial"] for row in archive})
    return None, opening[index % len(opening)], {"reason": "opening_probe", "opening_trial": index + 1}


def measured_group_changes(summary):
    changes = summary.get("partition_changes_vs_initial") or {}
    return changes.get("reported_cells", 0) - changes.get("kept_up_to_swap", 0)


def measured_opening_parent(history, archive):
    """Give a measured candidate a bounded follow-up when the baseline comparison is mixed."""
    if not any((row.get("attempt") or {}).get("opening_trial") for row in archive):
        return None
    used = [row.get("attempt", {}).get("parent_id") for row in archive]
    eligible = [
        result for result, summary in zip(history, archive)
        if result["status"] == "succeeded" and result.get("source") and not summary.get("duplicate_of")
        and measured_group_changes(summary) >= 2 and used.count(result["candidate_id"]) < 2
        and not (summary.get("parent_comparison") or {}).get("candidate_invalid_cells")
        and (summary.get("ablation_result") or {}).get("status") not in ("failed", "unverified")
    ]
    return max(eligible, key=score_key, default=None)


def design_combination(history, archive):
    """Transplant a measured component when standalone candidates have complementary results."""
    if len(history) != OPENING_TRIALS or not all(
            (row.get("attempt") or {}).get("opening_trial") for row in archive):
        return None
    trials = []
    for result, summary in zip(history, archive):
        attempt = summary["attempt"]
        edited = tuple(attempt.get("changed_components", {}))
        comparison = summary.get("parent_comparison") or {}
        if (result["status"] == "succeeded" and result.get("source") and len(edited) == 1
                and edited[0] in ("loss", "decoder") and not summary.get("duplicate_of")
                and comparison.get("complete") and not comparison.get("candidate_invalid_cells")):
            trials.append((result, edited[0], attempt["parent_id"]))
    if len(trials) < 2:
        return None

    best_score = max(score_key(result)[0] for result, _, _ in trials)
    evidence = {summary["candidate_id"]: summary for summary in archive}
    near_best = [row for row in trials if score_key(row[0])[0] >= best_score - ABLATION_MARGIN]
    control, control_component, start_id = max(
        near_best, key=lambda row: (
            measured_group_changes(evidence[row[0]["candidate_id"]]), row[1] == "loss", score_key(row[0])
        ),
    )
    schedule = control["feedback"]["cells"]
    options = []
    for donor, component, donor_start in trials:
        if component == control_component or start_id != donor_start:
            continue
        paired = compare_feedback(control, donor, schedule)
        if not paired["complete"]:
            continue
        gains = [row for row in paired["cells"] if row["score_delta"] >= ABLATION_MARGIN]
        protected = [row for row in paired["cells"] if row["score_delta"] <= -ABLATION_MARGIN]
        if len(gains) < 2 or not protected:
            continue
        sources = (control["source"], donor["source"]) if component == "decoder" else (donor["source"], control["source"])
        functions = [ast.get_source_segment(source, ast.parse(source).body[index])
                     for index, source in enumerate(sources)]
        try:
            combined = validate_program("\n\n".join(functions), DECODER_TASK)
            candidate_gate(combined)
        except (TypeError, ValueError, SyntaxError):
            continue
        if function_keys(combined) in {function_keys(row["source"]) for row, _, _ in trials}:
            continue
        target = max(gains, key=lambda row: row["score_delta"])
        key_fields = ("case", "seed", "score_delta", "wns_slack_delta_ns", "tns_slack_delta_ns")
        decision = {
            "reason": "test_complementary_components",
            "component": component,
            "component_donor": donor["candidate_id"],
            "combination_source": combined,
            "ablation": {
                "diagnosis_reference": "run_evaluation",
                "target": {key: target[key] for key in key_fields},
                "protected_cells": [{key: row[key] for key in key_fields} for row in protected],
                "minimum_target_gain": ABLATION_MARGIN,
                "maximum_protected_loss": ABLATION_MARGIN,
                "maximum_case_mean_loss": ABLATION_MARGIN,
            },
        }
        options.append(((len(gains), mean(row["score_delta"] for row in gains), score_key(donor)), decision))
    if options:
        return control, "repair", max(options, key=lambda option: option[0])[1]
    return None


def lineage_head(history, archive):
    """Best candidate reached from the start through broad paired gains only; None means the start.

    Final selection still uses the official score. The lineage only decides which parent the next
    hypothesis builds on, so a gain carried by one cell or by a die exchange is kept as a candidate
    but is not extended.
    """
    members = {}
    for result, summary in zip(history, archive):
        if (summary.get("attempt") or {}).get("ablation"):
            if result["status"] == "succeeded" and (summary.get("ablation_result") or {}).get("status") == "passed":
                members[result["candidate_id"]] = result
            continue
        evidence = trial_evidence(summary) if result["status"] == "succeeded" else None
        comparison = summary.get("parent_comparison") or {}
        parent_id = (summary.get("attempt") or {}).get("parent_id")
        if evidence and evidence["reason"] == "broad_gain" and (
                comparison.get("parent_source") == "published_initial_reference" or parent_id in members):
            members[result["candidate_id"]] = result
    return max(members.values(), key=score_key, default=None)


def select_parent(history, best, archive, initial_reference, opening=OPENING):
    if not history:
        return opening_probe(archive, opening)

    latest, feedback = history[-1], archive[-1]
    failures = [cell["failure"] for cell in feedback.get("cells", []) if "failure" in cell]
    infrastructure = bool(failures) and all(failure["kind"] == "runtime_environment" for failure in failures)
    attempt = feedback.get("attempt") or {}
    if infrastructure and latest.get("source") and not attempt.get("retry_of") and not attempt.get("retry_refused"):
        comparison = feedback.get("parent_comparison") or {}
        retried = any((row.get("attempt") or {}).get("retry_of") == latest["request_id"] for row in archive)
        median = comparison.get("median_paired_score_delta")
        if not retried and (not comparison.get("scored_pairs") or median is None or median >= 0):
            # The hypothesis was not measured. Resubmit the same source once, without a model call.
            return latest, "retry", {"reason": "runtime_environment_retry", "candidate_id": latest["candidate_id"]}

    contract = next((failure for failure in failures if failure["kind"] == "candidate_contract"), None)
    if contract and contract["component"]:
        # Repair the candidate that broke the contract, so its hypothesis is still measured.
        return latest if latest.get("source") else best, "repair", {
            "reason": "candidate_contract_failure", "candidate_id": latest["candidate_id"],
            "component": contract["component"],
        }

    probe = opening_probe(archive, opening)
    if probe is not None:
        return probe
    if not failures and not attempt.get("ablation"):
        followup = seed_followup(history, archive)
        if followup:
            return followup
    combination = design_combination(history, archive)
    if combination is not None:
        return combination
    if len(history) == OPENING_TRIALS:
        control = measured_opening_parent(history, archive)
        if control is not None:
            measured = next(row for row in archive if row["candidate_id"] == control["candidate_id"])
            edited = tuple(measured.get("attempt", {}).get("changed_components", {}))
            intent = {("loss",): "decoder_only", ("decoder",): "loss_only"}.get(edited, "refine")
            return control, intent, {"reason": "continue_measured_opening", "evidence": trial_evidence(measured)}

    if attempt.get("ablation") and not contract:
        outcome = (feedback.get("ablation_result") or {}).get("status")
        if outcome == "passed":
            return latest, "refine", {"reason": "ablation_passed", "ablation_result": feedback["ablation_result"]}
        control = next((row for row in history if row["candidate_id"] == attempt.get("parent_id")
                        and row["status"] == "succeeded"), None)
        if control:
            edited = attempt.get("changed_components") or {}
            other = "decoder_only" if "loss" in edited else "loss_only"
            return control, other, {"reason": "keep_measured_ablation_control",
                                    "ablation_result": feedback.get("ablation_result")}
    ablation = design_ablation(archive) if not failures else None
    if ablation:
        return latest, "repair", ablation

    if len(history) == 1 and latest["status"] == "succeeded":
        evidence = trial_evidence(feedback)
        ambiguous = feedback.get("timing_changes_with_identical_assignment")
        if evidence and evidence["reason"] == "broad_gain" and evidence["cases"] >= 2 and not ambiguous:
            return latest, opening[0], {"reason": "refine_supported_opening", "evidence": evidence}
        return None, opening[1], {"reason": "test_alternative_component_after_opening", "evidence": evidence,
                                  "largest_regression": (feedback.get("parent_comparison") or {})
                                  .get("largest_regression")}

    head = lineage_head(history, archive) or measured_opening_parent(history, archive)
    if infrastructure:
        return head, "refine" if head else "diversify", {
            "reason": "runtime_environment_failure", "candidate_id": latest["candidate_id"],
        }
    if best is None:
        return None, "diversify", {"reason": "no_complete_candidate"}

    # An inconclusive trial (labels kept, dies exchanged, or a gain carried by one cell) does not move
    # the lineage: the next hypothesis builds on the lineage head, not on the trial or on the start.
    evidence = trial_evidence(feedback)
    reason = (evidence or {}).get("reason")
    if reason in ("orientation_only", "partition_mostly_unchanged", "timing_mostly_unchanged", "duplicate_outcome"):
        edited = tuple((feedback.get("attempt") or {}).get("changed_components", {}))
        intent = {("loss",): "decoder_only", ("decoder",): "loss_only"}.get(edited, "diversify")
        if edited == ("loss",) and reason != "duplicate_outcome":
            # The decoder sees only embeddings, so the loss is the lever on which groups share a die; in
            # every recorded run a decoder edit from the start only exchanged the dies. A loss term too weak
            # to move the labels is strengthened once before the decoder is tried.
            inert_losses = 0
            for row in reversed(archive):
                previous = trial_evidence(row) or {}
                if (tuple((row.get("attempt") or {}).get("changed_components", {})) != ("loss",)
                        or previous.get("reason") not in ("partition_mostly_unchanged", "timing_mostly_unchanged")):
                    break
                inert_losses += 1
            if inert_losses < 2:
                return head, "loss_only", {"candidate_id": latest["candidate_id"], **evidence,
                                           "next_step": "strengthen_the_loss_term_so_labels_move"}
        return head, intent, {"candidate_id": latest["candidate_id"], **evidence}
    if reason == "narrow_gain":
        return head, "diversify", {"candidate_id": latest["candidate_id"], **evidence}

    comparison = feedback.get("parent_comparison") or {}
    score_delta = comparison.get("official_score_delta")
    if comparison.get("complete") and score_delta is not None and score_delta < 0:
        regression = comparison["largest_regression"]
        improved, regressed = comparison["improved_pairs"], comparison["regressed_pairs"]
        paired = comparison["scored_pairs"]
        attempt = feedback.get("attempt", {})
        if (regression and improved > paired // 2 and 0 < regressed <= max(1, paired // 3)
                and not comparison["candidate_invalid_cells"] and attempt.get("search_intent") != "repair"):
            decision = {"reason": "concentrated_regression", "largest_regression": regression}
            edited = attempt.get("changed_components", {})
            if len(edited) == 1:
                decision["component"] = next(iter(edited))
            return latest, "repair", decision
        if reason == "broad_regression":
            return head, "diversify", {"candidate_id": latest["candidate_id"], **evidence}
    if head is None:
        return None, "diversify", {"reason": "start_still_ahead"}
    head_index = next(index for index, result in enumerate(history)
                      if result["request_id"] == head["request_id"])
    rounds_without_gain = len(history) - head_index - 1
    if rounds_without_gain and rounds_without_gain % 2 == 0:
        return head, "diversify", {"reason": "search_plateau"}
    return head, "refine", {"reason": "refine_best"}


def save_best(folder, result):
    pending = folder / "program.py.pending"
    pending.write_text(result["source"], encoding="utf-8")
    pending.replace(folder / "program.py")


def claim_once(context, filename):
    workspace = Path(context.files.get("workspaces", "/workspace/workspaces"))
    try:
        with (workspace / filename).open("x", encoding="utf-8"):
            return True
    except FileExistsError:
        return False


def published_initial_reference(context):
    table = reference_table()["cases"]
    cells = []
    for cell in context.evaluation_cells:
        case, seed = cell["case"], str(cell["seed"])
        entry = table.get(case, {})
        sample = entry.get("measurements", {}).get(context.task, {}).get(seed)
        if entry.get("split") != "train" or sample is None:
            return None
        metrics = score_metrics(case, {
            "runs_successfully": 1, "sta_graph_complete": 1,
            "timing_evaluation_boundary": "post-opt-pre-cts", "combined_score": 0,
            "final_global_wns_setup_ns": sample["wns_ns"], "final_global_tns_setup_ns": sample["tns_ns"],
        })
        cells.append({"case": case, "seed": seed, "status": "published_reference",
                      "score": metrics["combined_score"], "metrics": metrics})
    if not cells:
        return None
    cases = {cell["case"] for cell in cells}
    score = mean(mean(cell["score"] for cell in cells if cell["case"] == case) for case in sorted(cases))
    return {"candidate_id": context.baseline_candidate, "status": "published_reference",
            "feedback": {"score": score, "cells": cells}}


def same_host_start(published, history, partitions):
    """The start reference with each cell measured on this host where a receipt kept the start assignment.

    A receipt with the unchanged assignment is a same-host proxy. If its timing disagrees with
    another zero-change receipt, use the published value and mark the cell as unverified on this host.
    """
    if published is None:
        return None
    measured = {}
    conflicts = set()
    timing_fields = ("final_global_wns_setup_ns", "final_global_tns_setup_ns")
    published_keys = {(cell["case"], str(cell["seed"])) for cell in published["feedback"]["cells"]}
    for result in history:
        if result["status"] != "succeeded":
            continue
        changes = partitions.get(result["request_id"]) or {}
        for cell in result["feedback"]["cells"]:
            key = cell["case"], str(cell["seed"])
            score = cell.get("score")
            if (key not in published_keys or key in conflicts
                    or changes.get(key, {}).get("partition_assignment_changed_count") != 0
                    or cell.get("status") != "succeeded" or not isinstance(score, (int, float))
                    or not isfinite(score)):
                continue
            previous = measured.get(key)
            if previous is not None:
                mismatched = not isclose(previous["score"], score, rel_tol=0.0, abs_tol=1e-7)
                for field in timing_fields:
                    a = (previous.get("metrics") or {}).get(field)
                    b = (cell.get("metrics") or {}).get(field)
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        mismatched |= not isclose(a, b, rel_tol=0.0, abs_tol=1e-7)
                if mismatched:
                    conflicts.add(key)
                    del measured[key]
                    continue
            measured.setdefault(key, cell)
    if not measured and not conflicts:
        return published
    cells = []
    for cell in published["feedback"]["cells"]:
        same = measured.get((cell["case"], str(cell["seed"])))
        cells.append({**cell, "score": same["score"], "metrics": same.get("metrics") or {},
                      "measured_on": "this_host"} if same else {**cell, "measured_on": "published"})
    cases = sorted({cell["case"] for cell in cells})
    score = mean(mean(cell["score"] for cell in cells if cell["case"] == case) for case in cases)
    return {**published, "feedback": {"score": score, "cells": cells},
            "summary": {"same_host_cells": len(measured), "published_cells": len(cells) - len(measured),
                        "same_host_score": score, "published_score": published["feedback"]["score"],
                        "score_kind": "measured" if len(measured) == len(cells) else "mixed_reference",
                        "conflicting_cells_using_published": [list(key) for key in sorted(conflicts)]}}


def bridge(call, *args, attempts=BRIDGE_ATTEMPTS):
    """Repeat a read-only bridge call through transient socket errors."""
    for attempt in range(attempts):
        try:
            return call(*args)
        except AgentAPIError:
            if attempt + 1 == attempts:
                raise
            time.sleep(min(60, 5 * 2 ** attempt))


def summarize_cell(cell):
    summary = {key: cell[key] for key in ("case", "seed", "score", "raw_score", "valid", "status", "metrics") if key in cell}
    reason = cell.get("reason") or cell.get("error_message")
    if reason:
        summary["reason"] = str(reason)[:400]
    evidence = failure_evidence(cell)
    if evidence is not None:
        summary["failure"] = evidence
    return summary


def summarize(result):
    feedback = result.get("feedback", {})
    cells = feedback.get("cells", [])
    case_scores = {}
    for cell in cells:
        if isinstance(cell.get("score"), (int, float)):
            case_scores.setdefault(cell["case"], []).append(cell["score"])
    return {
        "request_id": result["request_id"],
        "candidate_id": result["candidate_id"],
        "status": result["status"],
        "reason": str(result.get("reason") or "")[:400],
        "score": feedback.get("score"),
        "case_scores": {case: {"mean": mean(scores), "worst_seed_score": min(scores),
                               "scored_seeds": len(scores)} for case, scores in case_scores.items()},
        "cells": [summarize_cell(cell) for cell in cells],
    }


def write_event(folder, event, **fields):
    with (folder / "search.jsonl").open("a+b") as log:
        log.seek(0, 2)
        separator = b""
        if log.tell():
            log.seek(-1, 2)
            if log.read(1) != b"\n":
                separator = b"\n"
        line = json.dumps({"event": event, **fields}, ensure_ascii=False)
        log.write(separator + line.encode("utf-8") + b"\n")


def submit_and_wait(context, source, request_id):
    """Submit once; raise AgentAPIError only when the bridge has no record of the request."""
    try:
        result = context.submit_evaluation(source, request_id=request_id)
    except AgentAPIError:
        if not any(row["request_id"] == request_id for row in bridge(context.status)["history"]):
            raise
    else:
        if result["status"] in {"succeeded", "failed", "rejected"}:
            return result
    return bridge(context.wait_evaluation, request_id)


class Agent:
    uses_separate_planning = True

    def run(self, context):
        """Search, and on any unexpected error after a complete evaluation, return the best candidate.

        A crash in feedback analysis must not discard the evaluations already spent: the official
        result needs a candidate ID, and an exception from Agent.run fails the whole formal run.
        """
        self.best = None
        try:
            return self._search(context)
        except Exception as error:
            if self.best is None:
                raise
            folder = Path(__file__).resolve().parent
            write_event(folder, "agent_error", error=f"{type(error).__name__}: {error}"[:400],
                        traceback=traceback.format_exc()[-2000:])
            write_event(folder, "selected", selection={"rule": "highest_official_score_after_agent_error"},
                        **summarize(self.best))
            return self.best["candidate_id"]

    def _search(self, context):
        if context.task != "loss_decoder":
            raise ValueError("This Agent implements the loss_decoder baseline")
        folder = Path(__file__).resolve().parent
        opening = OPENING
        opening_file = folder / "opening.txt"
        if opening_file.is_file():
            first = opening_file.read_text(encoding="utf-8").strip()
            if first not in OPENING:
                raise ValueError("Opening must be loss_only or decoder_only")
            opening = (first, next(intent for intent in OPENING if intent != first))
        task = Path(context.files["framework"]) / "local_tasks" / DECODER_TASK
        initial = validate_program((task / "initial_program.py").read_text(encoding="utf-8"), DECODER_TASK)
        instructions, marker, experience = (folder / "prompt.md").read_text(encoding="utf-8").partition(EXPERIENCE_HEADING)
        interface = (task / "prompt.md").read_text(encoding="utf-8")

        state = bridge(context.status)
        history = []
        attempts = load_attempts(folder / "search.jsonl")
        receipts_by_candidate = {}
        partition_cache = {}
        evaluation_root = context.files.get("evaluations", "/workspace/evaluations")
        cpu = CPUChecks(context.files)
        rejected_combinations = set()
        initial_reference = published_initial_reference(context)
        if initial_reference is not None:
            receipts_by_candidate[context.baseline_candidate] = initial_reference

        def partition_for(result):
            request_id = result["request_id"]
            if request_id not in partition_cache:
                partition_cache[request_id] = published_partition_changes(result, evaluation_root)
            return partition_cache[request_id]

        def refresh_start():
            try:
                start = same_host_start(initial_reference, history,
                                        {result["request_id"]: partition_for(result) for result in history})
            except Exception as error:
                write_event(folder, "analysis_error", stage="start_reference",
                            error=f"{type(error).__name__}: {error}"[:400])
                start = initial_reference
            if start is not None:
                receipts_by_candidate[context.baseline_candidate] = start
            return start

        snapshot_cache, fingerprints, analysis_errors = {}, {}, set()

        def fingerprint(result):
            if result["request_id"] not in fingerprints:
                fingerprints[result["request_id"]] = outcome_fingerprint(result)
            return fingerprints[result["request_id"]]

        def assignments_vs_parent(result, parent_id):
            """Measured label changes from a candidate parent, read from both published label files."""
            parent = receipts_by_candidate.get(parent_id)
            if parent is None or parent.get("status") != "succeeded" or parent_id == result["candidate_id"]:
                return {}
            changes = {}
            for cell in result["feedback"]["cells"]:
                key = cell["case"], str(cell["seed"])
                change = assignment_difference(assignment_snapshot(parent, evaluation_root, key, snapshot_cache),
                                               assignment_snapshot(result, evaluation_root, key, snapshot_cache))
                if change is not None:
                    changes[key] = change
            return changes

        def summarize_for_prompt(result):
            """The analysed receipt; on an analysis error, the plain receipt summary and the error."""
            try:
                return analyse(result)
            except Exception as error:
                if result["request_id"] not in analysis_errors:
                    analysis_errors.add(result["request_id"])
                    write_event(folder, "analysis_error", request_id=result["request_id"],
                                error=f"{type(error).__name__}: {error}"[:400], traceback=traceback.format_exc()[-1500:])
                summary = summarize(result)
                summary["analysis_error"] = type(error).__name__
                attempt = attempts.get(result["request_id"])
                if attempt:
                    summary["attempt"] = attempt
                return summary

        def analyse(result):
            summary = summarize(result)
            own = fingerprint(result)
            if own is not None:
                for earlier in history:
                    if earlier["request_id"] == result["request_id"]:
                        break
                    if earlier["candidate_id"] != result["candidate_id"] and fingerprint(earlier) == own:
                        summary["duplicate_of"] = earlier["candidate_id"]
                        break
            partition = partition_for(result)
            if partition:
                moved, swaps = {}, set()
                for key, row in partition.items():
                    fraction = row.get("partition_assignment_changed_fraction")
                    if row["partition_assignment_changed_count"] == 0:
                        moved[key] = 0.0
                    elif isinstance(fraction, (int, float)):
                        moved[key] = min(fraction, 1 - fraction)
                        if fraction > SWAP_FRACTION:
                            swaps.add(key)
                summary["partition_changes_vs_initial"] = {
                    "reported_cells": len(partition),
                    "identical_assignments": sum(row["partition_assignment_changed_count"] == 0
                                                 for row in partition.values()),
                    "die_swaps": len(swaps),
                    "kept_up_to_swap": sum(value < KEPT_UP_TO_SWAP for value in moved.values()),
                }
                for cell in summary["cells"]:
                    key = cell["case"], str(cell["seed"])
                    change = partition.get(key)
                    if change is not None:
                        cell["partition_change_vs_initial"] = {**change, "die_swap_vs_initial": key in swaps}
                        if key in moved:
                            cell["partition_change_vs_initial"]["moved_fraction_up_to_swap"] = moved[key]
            attempt = attempts.get(result["request_id"], {})
            if attempt:
                summary["attempt"] = attempt
            comparison = comparison_for_prompt(result, attempt.get("parent_id"), receipts_by_candidate,
                                               context.evaluation_cells,
                                               assignments_vs_parent(result, attempt.get("parent_id"))
                                               if result["status"] == "succeeded" else None)
            if comparison is not None:
                summary["parent_comparison"] = comparison
                if attempt.get("ablation"):
                    summary["ablation_result"] = assess_ablation(attempt["ablation"], comparison)
                if attempt.get("component_donor"):
                    donor_pair = comparison_for_prompt(
                        result, attempt["component_donor"], receipts_by_candidate, context.evaluation_cells,
                        assignments_vs_parent(result, attempt["component_donor"])
                        if result["status"] == "succeeded" else None,
                    )
                    if donor_pair is not None:
                        summary["donor_pair"] = {key: donor_pair[key] for key in (
                            "official_score_delta", "largest_regression", "largest_gain"
                        ) if key in donor_pair}
                if comparison.get("parent_source") == "published_initial_reference":
                    discrepancies = [
                        {key: cell[key] for key in ("case", "seed", "score_delta", "wns_slack_delta_ns", "tns_slack_delta_ns")}
                        for cell in comparison["cells"]
                        if partition.get((cell["case"], cell["seed"]), {}).get("partition_assignment_changed_count") == 0
                        and abs(cell["score_delta"]) > 1e-6
                    ]
                    if discrepancies:
                        summary["timing_changes_with_identical_assignment"] = sorted(
                            discrepancies, key=lambda cell: abs(cell["score_delta"]), reverse=True)[:3]
            return summary

        seen = {function_keys(initial)}
        best = None

        def record(result, logged=True):
            nonlocal best
            history.append(result)
            if result.get("source"):
                seen.add(function_keys(result["source"]))
            if result["status"] == "succeeded":
                receipts_by_candidate[result["candidate_id"]] = result
                if best is None or score_key(result) > score_key(best):
                    best = self.best = result
                    if logged:
                        save_best(folder, best)
                        write_event(folder, "incumbent", **summarize(best))

        for row in state["history"]:
            record(bridge(context.wait_evaluation, row["request_id"]), logged=False)
        if best is not None:
            save_best(folder, best)

        issue = None
        initial_experience_pending = bool(marker and not history)
        consecutive_api_failures = 0
        plan_cache = {}
        consecutive_invalid = 0
        shorten_next = False
        while True:
            state = bridge(context.status)
            known = {result["request_id"] for result in history}
            for row in state["history"]:
                if row["request_id"] not in known:  # accepted while its reply was lost
                    result = bridge(context.wait_evaluation, row["request_id"])
                    write_event(folder, "evaluated", **summarize_for_prompt(result))
                    record(result)
            if not state["evaluation_dispatch_allowed"]:
                write_event(folder, "budget_stop", evaluations_remaining=state["evaluations_remaining"],
                            model_stop_reasons=state["model_stop_reasons"])
                break

            start = refresh_start()
            archive = [summarize_for_prompt(result) for result in history]
            try:
                parent, intent, decision = select_parent(history, best, archive, start, opening)
            except Exception as error:
                # Keep spending the budget from the best candidate rather than stopping the run.
                write_event(folder, "analysis_error", stage="select_parent",
                            error=f"{type(error).__name__}: {error}"[:400], traceback=traceback.format_exc()[-1500:])
                parent, intent, decision = best, ("refine" if best else "diversify"), {"reason": "analysis_error"}
            combination_source = decision.pop("combination_source", None)
            if combination_source in rejected_combinations:
                combination_source = None
                intent = decision["component"] + "_only"
                decision = {"reason": "replace_invalid_combination", "component": decision["component"]}
            if not state["model_dispatch_allowed"] and combination_source is None and intent != "retry":
                write_event(folder, "budget_stop", evaluations_remaining=state["evaluations_remaining"],
                            model_stop_reasons=state["model_stop_reasons"])
                break
            if intent == "retry":
                request_id = "r-" + parent["request_id"][2:]
                attempt = {**attempts.get(parent["request_id"], {}), "retry_of": parent["request_id"]}
                attempts[request_id] = attempt
                write_event(folder, "submitted", request_id=request_id, decision=decision, **attempt)
                try:
                    result = submit_and_wait(context, parent["source"], request_id)
                except AgentAPIError as error:
                    attempts.pop(request_id, None)
                    attempts[parent["request_id"]] = {**attempts.get(parent["request_id"], {}),
                                                      "retry_refused": str(error)[:200]}
                    write_event(folder, "retry_refused", request_id=parent["request_id"], reason=str(error)[:400])
                    continue
                write_event(folder, "evaluated", parent_id=attempt.get("parent_id"), **summarize_for_prompt(result))
                record(result)
                continue
            parent_id = parent["candidate_id"] if parent else context.baseline_candidate
            parent_source = parent["source"] if parent else initial
            summaries = {row["request_id"]: row for row in archive}
            parent_feedback = summaries[parent["request_id"]] if parent else None
            incumbent_feedback = summaries[best["request_id"]] if best and best is not parent else None
            displayed = {row["request_id"] for row in (parent_feedback, incumbent_feedback) if row is not None}
            if archive:
                displayed.add(archive[-1]["request_id"])
            focus = parent_feedback or incumbent_feedback
            if archive and any("failure" in cell for cell in archive[-1]["cells"]):
                focus = archive[-1]
            request = {
                "search_intent": intent,
                "decision": decision,
                "parent_id": parent_id,
                "parent_program": parent_source,
                "training_cells": context.evaluation_cells,
                "evaluations_remaining": state["evaluations_remaining"],
                "incumbent_feedback": compact_feedback(incumbent_feedback),
                "prior_trials": [summarize_trial(row) for row in archive[-4:]],
                "related_experiment": related_experiment(focus, archive, displayed),
                "previous_generation_issue": issue,
            }
            request["experiment_record"] = experiment_record(
                initial, parent_source, parent_id, start, archive, context.evaluation_cells,
                cpu.evidence([parent_feedback, archive[-1] if archive else None], archive))
            if start is not None and start.get("summary"):
                request["start_reference"] = start["summary"]
            system_prompt = instructions.rstrip() + "\n\n" + interface
            if decision.get("opening_trial"):
                system_prompt += "\n\n" + OPENING_TASK
            if decision.get("ablation"):
                system_prompt += "\n\n" + ABLATION_TASK
            plan_key = len(history), parent_id, intent
            if combination_source is None:
                try:
                    if plan_key not in plan_cache:
                        planner_prompt = (PLAN_TASK + "\n\nUse the case and seed from history.seed_results for each "
                                          "observation. Check the other seeds of the same design before generalizing; "
                                          "name a target and a gain to preserve when available, and specify a falsifier.\n\n"
                                          + interface)
                        if decision.get("opening_trial"):
                            planner_prompt += "\n\n" + OPENING_TASK
                        if decision.get("ablation"):
                            planner_prompt += "\n\n" + ABLATION_TASK
                        first_planner_prompt = planner_prompt
                        if initial_experience_pending:
                            initial_experience_pending = False
                            if claim_once(context, "loss-decoder-initial-prompt-sent"):
                                first_planner_prompt += "\n\n" + marker + experience
                        plan_cache[plan_key] = ""
                        # An over-long or empty plan gets one shorter, lower-effort attempt before code generation
                        # proceeds without a plan.
                        for effort, planning_request, plan_prompt in (("high", request, first_planner_prompt),
                                                                     ("low", shortened(request), planner_prompt)):
                            try:
                                plan_cache[plan_key] = model_text(
                                    ask_model(context, plan_prompt, planning_request, effort, "plan"))[:1800]
                                break
                            except ValueError as error:
                                write_event(folder, "plan_unavailable", parent_id=parent_id, effort=effort,
                                            reason=str(error)[:250])
                                if not bridge(context.status)["model_dispatch_allowed"]:
                                    break
                            except AgentAPIError as error:
                                write_event(folder, "plan_unavailable", parent_id=parent_id, effort=effort,
                                            reason=str(error)[:250])
                                break
                    if not bridge(context.status)["model_dispatch_allowed"]:
                        write_event(folder, "stop_before_codegen", parent_id=parent_id)
                        break
                    generation = {key: request[key] for key in (
                        "search_intent", "decision", "parent_id", "parent_program", "training_cells",
                        "evaluations_remaining", "previous_generation_issue", "experiment_record",
                    )}
                    generation["experiment_plan"] = plan_cache[plan_key]
                    generation["prior_trials"] = request["prior_trials"][-4:]
                    focus_comparison = (focus or {}).get("parent_comparison") or {}
                    generation["largest_regression"] = focus_comparison.get("largest_regression")
                    if not plan_cache[plan_key]:
                        generation["incumbent_feedback"] = request["incumbent_feedback"]
                    if shorten_next:
                        generation = shortened(generation)
                    response = ask_model(context, system_prompt, generation)
                except AgentAPIError as error:
                    issue = str(error)
                    write_event(folder, "model_error", parent_id=parent_id, reason=issue)
                    consecutive_api_failures += 1
                    if consecutive_api_failures >= 5:
                        break
                    time.sleep(min(60, 2 ** consecutive_api_failures))
                    continue
                consecutive_api_failures = 0

            try:
                source = combination_source or generated_program(response)
                parent_key = function_keys(parent_source)
                unchanged = UNCHANGED_FUNCTION.get(intent)
                if intent == "repair" and "component" in decision:
                    unchanged = UNCHANGED_FUNCTION[decision["component"] + "_only"]
                key = proposal_keys(source, parent_key, unchanged, seen)
                if decision.get("reason") == "repair_within_case_seed_tradeoff" and sum(
                        a != b for a, b in zip(key, parent_key)) != 1:
                    raise ValueError("Change exactly one component to test the proposed seed tradeoff")
                if decision.get("opening_trial") == OPENING_TRIALS:
                    index = 0 if intent == "loss_only" else 1
                    shape = function_keys(source, compare_structure=True)[index]
                    if any(result.get("source") and function_keys(result["source"], True)[index] == shape
                           for result in history):
                        raise ValueError("Try a different opening mechanism instead of changing the constants "
                                         "or names in a component already tried")
                # The bridge deduplicates this ID if the submit acknowledgement is lost.
                request_id = "e-" + hashlib.sha256(repr(key).encode("utf-8")).hexdigest()[:60]
                if any(row["request_id"] == request_id for row in history):
                    raise ValueError("That program already has an official evaluation record")
                candidate_gate(source)
                validate_program(source, DECODER_TASK)
                preflight = cpu.run_check("contract", request_id, parent_id, parent_source, source)
                write_event(folder, "cpu_contract", request_id=request_id, **preflight)
                if preflight["status"] == "invalid":
                    raise ValueError("Synthetic contract failure on seed {}: {}".format(
                        preflight["seed"], preflight["issue"]))
            except (ValueError, SyntaxError) as error:
                if combination_source:
                    rejected_combinations.add(combination_source)
                issue = str(error)[:400]
                write_event(folder, "invalid_proposal", parent_id=parent_id, reason=issue)
                if issue.startswith("The model returned an incomplete response"):
                    # The reasoning used the whole output allowance. Ask again with less input.
                    issue = issue.rstrip(".") + ". Reply with the complete program only and keep the edit small."
                    shorten_next = True
                consecutive_invalid += 1
                if consecutive_invalid % REPLAN_AFTER_INVALID == 0 and plan_cache.pop(plan_key, None) is not None:
                    write_event(folder, "replan", parent_id=parent_id, reason=issue)
                if consecutive_invalid >= (STOP_AFTER_INVALID if best is not None else STOP_WITHOUT_CANDIDATE):
                    write_event(folder, "generation_stop", parent_id=parent_id, reason=issue)
                    break
                continue

            consecutive_invalid = 0
            shorten_next = False
            seen.add(key)
            hypotheses = {}
            for component, function, updated, previous in zip(
                    ("loss", "decoder"), ast.parse(source).body, key, parent_key):
                if updated != previous:
                    hypotheses[component] = " ".join((ast.get_docstring(function) or "").split())[:450]
            attempt = {"parent_id": parent_id, "search_intent": intent, "changed_components": hypotheses}
            attempt["plan"] = ("Recombine the two measured opening components and test target/protected cells."
                               if combination_source else plan_cache.get(plan_key, "")[:700])
            for field in ("opening_trial", "component_donor"):
                if field in decision:
                    attempt[field] = decision[field]
            if decision.get("ablation"):
                attempt["ablation"] = decision["ablation"]
            attempts[request_id] = attempt
            write_event(folder, "submitted", request_id=request_id, decision=decision, **attempt)
            control_id, control_source = ((context.baseline_candidate, initial) if combination_source
                                          else (parent_id, parent_source))
            cpu_status = cpu.start(request_id, control_id, control_source, source)
            write_event(folder, "cpu_ablation", request_id=request_id, control_id=control_id, status=cpu_status)
            try:
                result = submit_and_wait(context, source, request_id)
            except AgentAPIError as error:
                # The bridge has no record of this request, so no evaluation was spent on it.
                seen.discard(key)
                attempts.pop(request_id, None)
                write_event(folder, "submit_failed", request_id=request_id, reason=str(error)[:400])
                consecutive_api_failures += 1
                if consecutive_api_failures >= 5:
                    break
                time.sleep(min(60, 2 ** consecutive_api_failures))
                continue
            feedback = summarize_for_prompt(result)
            write_event(folder, "evaluated", parent_id=parent_id, **feedback)
            issue = None
            record(result)

        cpu.finish()
        if best is None:
            raise RuntimeError("No candidate completed an official training evaluation" + (f": {issue}" if issue else ""))
        chosen, selection = select_final(history, refresh_start(), best)
        if chosen is not best:
            save_best(folder, chosen)
        write_event(folder, "selected", selection=selection, **summarize(chosen))
        return chosen["candidate_id"]
