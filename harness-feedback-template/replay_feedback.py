"""Replay a local matched-candidate report through the training feedback adapter."""

import argparse
import json
from pathlib import Path

from paired_feedback import compare_feedback


def diagnostic_receipts(report):
    seeds = [row for case in report["cases"] for row in case["seeds"]]
    if report.get("formal_evaluation") is not False:
        raise ValueError("This replay accepts local diagnostic comparisons only.")

    def reply(prefix, candidate_id):
        return {
            "candidate_id": candidate_id, "status": "succeeded",
            "feedback": {"score": report["overall"][f"{prefix}_mean"], "cells": [
                {"case": row["case"], "seed": row["seed"], "score": row[prefix], "metrics": {
                    "final_global_wns_setup_ns": row[f"{prefix}_wns_ns"],
                    "final_global_tns_setup_ns": row[f"{prefix}_tns_ns"],
                    "cut_net_count": row[f"{prefix}_cut_nets"],
                }} for row in seeds]},
        }

    schedule = [{key: row[key] for key in ("case", "seed")} for row in seeds]
    return schedule, reply("initial", "diagnostic-initial"), reply("candidate", "diagnostic-candidate")


def replay(report):
    schedule, parent, candidate = diagnostic_receipts(report)
    summary = compare_feedback(parent, candidate, schedule)
    summary["source"] = "local_diagnostic_replay"
    summary["official_score_delta"] = None
    summary["diagnostic_mean_delta"] = report["overall"]["mean_change"]
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(json.loads(args.report.read_text(encoding="utf-8-sig"))),
                     ensure_ascii=False, indent=2, allow_nan=False))
