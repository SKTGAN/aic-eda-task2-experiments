"""One dossier per replay decision the patch changes (after original rounds 4, 7 and 9).

    DUMP_REQUESTS=<folder> python3 -I -B -m unittest discover -s tests -p "test_agent_integration.py"
    python3 -I -B tools/make_dossiers.py <folder>

Each dossier holds what the plan sees (ledger lessons, tolerances, the branching choice), the request a
high-effort planner would receive with PLAN_ON_OVERRIDE on, the two competing explanations and the
experiment that separates them, the gains to protect, the falsifier, the exact generation request the
patched Agent sent in the end-to-end replay, and the checks that ran on the generated program.
Development material only.
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


def plan_at(rounds, review_overrides=False):
    rows = replay.RUNS["claude-original"][:rounds]
    evidence = replay.ledger_for(rows)
    P.PLAN_ON_OVERRIDE = review_overrides
    try:
        plan = P.plan_next(evidence, replay.baseline("claude-original", rounds), 10 - rounds, 10, considered(rows))
    finally:
        P.PLAN_ON_OVERRIDE = False
    return evidence, plan


def generation_view(dump, index=-1):
    """The generation request the Agent sent, with field sizes."""
    rows = [row for row in dump if not row["system"].startswith("You plan one official experiment")]
    request = rows[index]["request"]
    return {"effort": rows[index]["effort"],
            "fields": {key: len(json.dumps(value, ensure_ascii=False)) for key, value in request.items()},
            "total_characters": len(json.dumps(request, ensure_ascii=False)),
            "search_intent": request["search_intent"], "parent_id": request["parent_id"],
            "decision": request["decision"], "experiment": request.get("experiment")}


def dossier(rounds, dump_name, dumps):
    evidence, plan = plan_at(rounds)
    _, reviewed = plan_at(rounds, review_overrides=True)
    packet = P.generation_packet(reviewed, reviewed["choice"], evidence)
    choice = plan["choice"]
    dump = json.loads((dumps / (dump_name + ".json")).read_text(encoding="utf-8"))
    return {
        "after_round": rounds,
        "branching_choice": plan["baseline"],
        "rolling_choice": {key: choice.get(key) for key in ("id", "kind", "parent", "component", "question",
                                                            "donors", "decides")},
        "evidence_the_plan_uses": {
            "lessons": [P.compact_lesson(row) for row in plan["lessons"]],
            "tolerances": plan["tolerances"],
            "decision_override": plan["decision_override"],
        },
        "competing_explanations": choice.get("hypotheses"),
        "experiment_that_separates_them": choice.get("distinguishes") or choice.get("question"),
        "gains_to_protect": (choice.get("contract") or {}).get("protect"),
        "falsifier": choice.get("falsifier") or (choice.get("contract") or {}).get("target"),
        "planner_request_if_overrides_are_reviewed": P.rounded(
            P.planner_request(reviewed, packet, sorted(T.ALLOWED_PROBES))),
        "generation_request_sent": generation_view(dump),
    }


def main():
    dumps = Path(sys.argv[1])
    dossiers = [dossier(4, "missing_control", dumps), dossier(7, "declined_repair_r7", dumps),
                dossier(9, "declined_repair_r9", dumps)]
    # The removal itself needs no generation call; the dump holds the follow-up after its outcome.
    dossiers[0]["generation_request_sent"]["note"] = (
        "Round 5 is the spliced removal, submitted with no model call. This is the round-6 request that followed "
        "it in the replay, where the hypothetical removal outcome (R4 minus 1 point) fell within tolerance.")
    for row, name in zip(dossiers, ("missing_control", "declined_repair_r7", "declined_repair_r9")):
        log = json.loads((dumps / (name + ".log.json")).read_text(encoding="utf-8"))
        submitted = [event for event in log if event["event"] == "submitted"][-1]
        row["checks_that_ran_on_the_generated_program"] = {
            "parent_id": submitted["parent_id"], "policy_action": submitted["policy_action"],
            "static": submitted["preflight"]["static"], "probes": submitted["preflight"]["probes"],
            "runtime": next(event for event in log if event["event"] == "runtime_capabilities")}
    out = ROOT / "examples"
    (out / "dossiers.json").write_text(json.dumps(P.rounded(dossiers, 5), indent=1, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    requests = out / "requests"
    requests.mkdir(exist_ok=True)
    for name in ("missing_control", "declined_repair_r7", "declined_repair_r9", "hard_branch", "old_control",
                 "preflight", "contract_request"):
        for suffix in (".json", ".log.json"):
            source = dumps / (name + suffix)
            if source.exists():
                (requests / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    for row in dossiers:
        sent = row["generation_request_sent"]
        print("R%d" % row["after_round"], row["rolling_choice"]["kind"], row["rolling_choice"]["parent"],
              row["rolling_choice"]["component"], "| sent:", sent["search_intent"], sent["decision"].get("reason"),
              sent["total_characters"], "chars")


if __name__ == "__main__":
    main()
