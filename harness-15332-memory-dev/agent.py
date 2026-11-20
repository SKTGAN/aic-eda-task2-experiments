"""Development continuation with a read-only archive and a separate two-evaluation ledger."""

import ast
import hashlib
import json
from pathlib import Path

from candidate_reply import generated_program, model_text
from contest2.agent_api import AgentAPIError
from memory import describe, measured_row, read_plan
from parent_harness import (DECODER_TASK, UNCHANGED_FUNCTION, ask_model, bridge, candidate_gate,
                            function_keys, proposal_keys, save_best, submit_and_wait, write_event)


HERE = Path(__file__).resolve().parent
CAP = 2
PLANNER = """You plan a new development experiment after the measured history below.
Read the whole chronology and compare mechanisms, parents, replicated gains and failures.
Choose the parent from the successful rounds. Prefer a supported gain; if a different parent is
better motivated, choose it. A failed decoder child does not invalidate its unchanged parent loss.
Separate comparisons within a host from score changes across hosts. Choose one generalizable
edit, identify which benefit is at risk, and describe a measurable falsifier. Case/seed names are
observations, never algorithm conditions. Return JSON only: parent_round (integer), component
("loss" or "decoder"), evidence (2-5 objects with integer round and exact cell key), and
experiment (under 120 words). Cite different rounds and include the latest new development
round if present. Account for evidence both for the parent and against repeating a previous edit."""


def observed():
    archive = json.loads((HERE / "ten-round-memory.json").read_text(encoding="utf-8"))
    rows = archive["rounds"]
    if not archive.get("development_only") or [r["round"] for r in rows] != list(range(1, 11)):
        raise ValueError("Missing the original ten-round development archive")
    programs = {}
    for row in rows:
        data = (HERE / "observed" / (row["candidate_id"] + ".py")).read_bytes()
        if hashlib.sha256(data).hexdigest() != row["source_sha256"]:
            raise ValueError("Historical source does not match the recorded digest")
        programs[row["round"]] = data.decode("utf-8")
    return rows, programs


def attempts():
    p = HERE / "search.jsonl"
    if not p.is_file():
        return {}
    events = (json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip())
    return {e["request_id"]: e for e in events if e["event"] == "development_proposal"}


def plan_turn(context, memory, rows):
    issue = None
    for effort in ("high", "medium", "low", "low"):
        request = {"memory": memory, "previous_issue": issue}
        response = ask_model(context, PLANNER, request, effort, "development_plan")
        try:
            return read_plan(model_text(response), rows)
        except (TypeError, ValueError) as error:
            issue = str(error)[:300]
            write_event(HERE, "invalid_plan", reason=issue)
    raise ValueError("Planner did not return a grounded parent and experiment: " + str(issue))


class Agent:
    def run(self, context):
        if context.task != "loss_decoder":
            raise ValueError("Wrong task for this development agent")
        rows, programs = observed()
        framework = Path(context.files["framework"]) / "local_tasks" / DECODER_TASK
        interface = (framework / "prompt.md").read_text(encoding="utf-8")
        instructions = (HERE / "editor.md").read_text(encoding="utf-8").split("## Offline Expert Knowledge")[0]
        instructions += "\nUse the complete measured memory and the chosen plan.\n" + interface
        seen = {function_keys(source) for source in programs.values()}
        seen.add(function_keys((framework / "initial_program.py").read_text(encoding="utf-8")))
        completed = {}
        while True:
            state = bridge(context.status)
            submitted = attempts()
            for entry in state["history"]:
                rid = entry["request_id"]
                if rid in completed:
                    continue
                meta = submitted[rid]
                result = bridge(context.wait_evaluation, rid)
                n = len(rows) + 1
                cells = result.get("feedback", {}).get("cells", [])
                score = result.get("feedback", {}).get("score")
                row = measured_row(n, "26016", result["candidate_id"], meta["parent_id"], score,
                                   cells, meta["changes"], result["status"])
                rows.append(row)
                source = result.get("source")
                if source:
                    programs[n] = source
                    seen.add(function_keys(source))
                completed[rid] = result
            if len(completed) >= CAP:
                break
            if not state["evaluation_dispatch_allowed"] or not state["model_dispatch_allowed"]:
                raise RuntimeError("Development budget unavailable for the next trial")
            memory = describe(rows)
            plan = plan_turn(context, memory, rows)
            parent = next(r for r in rows if r["round"] == plan["parent_round"])
            parent_source = programs[parent["round"]]
            intent = plan["component"] + "_only"
            parent_key = function_keys(parent_source)
            request = {"search_intent": intent, "parent_id": parent["candidate_id"], "parent_program": parent_source,
                       "memory": memory, "experiment_plan": plan, "previous_generation_issue": None}
            write_event(HERE, "development_decision", memory_rounds=[r["round"] for r in rows],
                        parent_id=parent["candidate_id"], plan=plan)
            for attempt in range(6):
                reply = ask_model(context, instructions, request, "low", "development_generation")
                try:
                    source = generated_program(reply)
                    proposal_keys(source, parent_key, UNCHANGED_FUNCTION[intent], seen)
                    candidate_gate(source)
                    break
                except (ValueError, SyntaxError) as error:
                    request["previous_generation_issue"] = str(error)[:450]
                    write_event(HERE, "invalid_proposal", reason=request["previous_generation_issue"])
            else:
                raise ValueError("Generator exhausted the development proposal retries")
            rid = "e-" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:60]
            component = plan["component"]
            func = ast.parse(source).body[0 if component == "loss" else 1]
            changes = {component: ast.get_docstring(func) or plan["experiment"]}
            write_event(HERE, "development_proposal", request_id=rid, parent_id=parent["candidate_id"],
                        memory_rounds=[r["round"] for r in rows], changes=changes, plan=plan)
            submit_and_wait(context, source, rid)
        valid = [r for r in completed.values() if r["status"] == "succeeded"]
        if not valid:
            raise RuntimeError("No successful development matrix")
        chosen = max(valid, key=lambda r: r["feedback"]["score"])
        save_best(HERE, chosen)
        write_event(HERE, "development_selected", candidate_id=chosen["candidate_id"], new_trials=len(completed))
        return chosen["candidate_id"]
