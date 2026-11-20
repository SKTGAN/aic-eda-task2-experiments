"""Write the review's worked examples from the archived prefixes (development material only).

    python3 -I -B tools/make_examples.py

Outputs examples/decisions.json (every recorded prefix: the branching choice and the rolling plan),
examples/planner_after_claude_round_6.json (a hard branch: what the planner receives, a sample
reply and the checked result) and examples/generation_after_evidence_round_3.json (exactly what code
generation receives). No model, bridge or evaluator is involved.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import replay  # noqa: E402
import ledger as L  # noqa: E402
import rolling_plan as P  # noqa: E402
import self_test as T  # noqa: E402


def considered(rows):
    return {(f["loss"], f["decoder"]) for f in (L.factor_ids(row["source"]) for row in rows)}


def plan_after(run, rounds):
    rows = replay.RUNS[run][:rounds]
    evidence = replay.ledger_for(rows)
    return evidence, P.plan_next(evidence, replay.baseline(run, rounds), 10 - rounds, 10, considered(rows))


def short(option):
    return {key: option.get(key) for key in ("id", "kind", "parent", "component", "question")}


decisions = {}
for run in ("claude-original", "ours-new"):
    rows = []
    for rounds in range(1, len(replay.RUNS[run]) + 1):
        evidence, plan = plan_after(run, rounds)
        actual = replay.RUNS[run][rounds] if rounds < len(replay.RUNS[run]) else None
        labels = {row["candidate_id"]: row["id"] for row in evidence["entries"]}
        rows.append({
            "after_round": rounds, "official_scores": [round(row["score"], 2) for row in replay.RUNS[run][:rounds]],
            "branching_choice": plan["baseline"], "rolling_choice": short(plan["choice"]),
            "options": [short(option) for option in plan["options"]], "planning_call": plan["hard"],
            "contract": P.rounded({key: (plan["choice"].get("contract") or {}).get(key) for key in ("target", "protect")}, 4),
            "lessons": P.rounded([P.compact_lesson(row) for row in plan["lessons"]], 4),
            "recorded_next": None if actual is None else {
                "parent": labels.get(actual["attempt"]["parent_id"], "S"),
                "component": list(actual["attempt"]["changed_components"]), "score": round(actual["score"], 2)},
        })
    decisions[run] = rows

out = ROOT / "examples"
out.mkdir(exist_ok=True)
(out / "decisions.json").write_text(json.dumps(decisions, indent=1) + "\n", encoding="utf-8")

evidence, plan = plan_after("claude-original", 6)
packet = P.generation_packet(plan, plan["choice"], evidence)
request = P.rounded(P.planner_request(plan, packet, sorted(T.ALLOWED_PROBES)))
reply = json.dumps({
    "choice": "X1",
    "explanations": ["R6 rewrote R4's decoder but kept every label, so the decoder rewrite was inert",
                     "R4's gain over R2 is three exchanged cells, so any decoder that keeps R2's grouping "
                     "can only re-roll the die orientation"],
    "discriminating_prediction": "a decoder that changes R2's grouping moves bp_fe by more than its 4.2-point tolerance "
                                 "on at least two seeds without exchanging the dies",
    "falsifier": "the new labels match R2 or R4 up to an exchange on most cells",
    "edit_brief": "rank boundary groups by area-normalised margin to the farther centre before the area cut",
    "probe": {"kind": "decoder_change_vs_parent", "min_fraction": 0.01, "max_fraction": 0.3}})
(out / "planner_after_claude_round_6.json").write_text(json.dumps({
    "system_prompt_head": P.PLAN_TASK, "request": request, "sample_reply": json.loads(reply),
    "checked": P.parse_plan_reply(reply, plan), "accepted_probe": T.accept_spec(json.loads(reply)["probe"]),
    "request_characters": len(json.dumps(request))}, indent=1) + "\n", encoding="utf-8")

evidence, plan = plan_after("ours-new", 3)
packet = P.rounded(P.generation_packet(plan, plan["choice"], evidence))
recorded = json.loads((ROOT / "tests" / "fixtures" / "ours_new_round4_request.json").read_text(encoding="utf-8"))["request"]
labels = {row["candidate_id"]: row["id"] for row in evidence["entries"]}
assembled = P.assemble_request(recorded, P.generation_packet(plan, plan["choice"], evidence), None, labels, True)
sizes = {key: [len(json.dumps(recorded.get(key), ensure_ascii=False)) if key in recorded else 0,
               len(json.dumps(assembled.get(key), ensure_ascii=False)) if key in assembled else 0]
         for key in sorted(set(recorded) | set(assembled))}
(out / "generation_after_evidence_round_3.json").write_text(json.dumps({
    "experiment_block": packet,
    "characters_by_field_recorded_vs_assembled": sizes,
    "total_characters": [len(json.dumps(recorded, ensure_ascii=False)), len(json.dumps(assembled, ensure_ascii=False))],
}, indent=1) + "\n", encoding="utf-8")
print({path.name: path.stat().st_size for path in sorted(out.iterdir())})
