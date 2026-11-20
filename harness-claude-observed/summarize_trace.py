"""Build a concise review index from a task-2 Agent search.jsonl file."""

import argparse
from collections import Counter
import json
from pathlib import Path


def summarize_trace(trace):
    events = []
    skipped_lines = 0
    for line in trace.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            skipped_lines += 1
            continue
        if isinstance(event, dict) and isinstance(event.get("event"), str):
            events.append(event)
        else:
            skipped_lines += 1

    replies = {event["call_id"]: event for event in events if event["event"] == "model_response"}
    calls = []
    for event in events:
        if event["event"] != "model_request":
            continue
        request = json.loads(event["payload"]["input"][1]["content"])
        reply = replies.get(event["call_id"], {})
        feedback = [request.get("parent_feedback"), request.get("incumbent_feedback"),
                    *request.get("recent_feedback", [])]
        calls.append({
            "call_id": event["call_id"],
            "purpose": event.get("purpose"),
            "search_intent": request.get("search_intent"),
            "evaluations_remaining": request.get("evaluations_remaining"),
            "feedback_request_ids": [item["request_id"] for item in feedback if item],
            "mechanism_ledger_entries": len(request.get("mechanism_ledger", [])),
            "reply_status": reply.get("status", "unrecorded"),
            "usage": reply.get("usage"),
        })

    evaluations = {}
    for event in events:
        if event["event"] in ("submitted", "evaluated"):
            request_id = event["request_id"]
            record = evaluations.setdefault(request_id, {})
            record[event["event"]] = {key: value for key, value in event.items()
                                      if key not in ("event", "request_id", "source")}

    return {
        "event_counts": dict(Counter(event["event"] for event in events)),
        "skipped_trace_lines": skipped_lines,
        "actual_model_input_recorded": bool(calls),
        "model_calls": calls,
        "evaluations_by_request_id": evaluations,
        "decisions": [event for event in events if event["event"] in (
            "policy_decision", "opening_review", "invalid_proposal", "decoder_probe", "budget_stop")
            or event["event"].startswith("selected")],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="Agent search.jsonl file")
    parser.add_argument("output", type=Path, help="Review index to write as UTF-8 JSON")
    args = parser.parse_args()
    args.output.write_text(json.dumps(summarize_trace(args.trace.read_bytes()), ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
