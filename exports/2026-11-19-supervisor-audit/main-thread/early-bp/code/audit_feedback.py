"""Audit exported round receipts and recorded main request bodies, without running candidate code."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile


def tree(value, path="input"):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from tree(child, path + "." + key)
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from tree(child, path + "[%d]" % index)


def next_request(bundle, arm, number, candidate, cells):
    member = f"{arm}/interactions/round-{number + 1:02}.jsonl"
    if member not in bundle.namelist():
        return {"status": "no_next_round_in_capture"}
    events = [json.loads(line) for line in bundle.read(member).splitlines() if line.strip()]
    for event in events:
        if event.get("event") != "model_request" or event.get("purpose") == "plan":
            continue
        body = json.loads(event["payload"]["input"][-1]["content"])
        if not {"parent_program", "training_cells", "search_intent"} <= body.keys():
            continue
        call = event["call_id"]
        response = next((j for j in events if j.get("event") == "model_response" and j.get("call_id") == call), {})
        audit = {"member": member, "main_request_call_id": call, "response_status": response.get("status"),
                 "status": "matching_structured_per_seed_fields_not_confirmed", "visible": {}}
        for path, node in tree(body):
            if node.get("candidate_id") != candidate or not isinstance(node.get("cells"), list):
                continue
            for entry in node["cells"]:
                seed = str(entry.get("seed"))
                if entry.get("case") != "bp-ng45" or seed not in cells:
                    continue
                timing = (entry.get("metrics") or {}).get("final_global_tns_setup_ns")
                count = (entry.get("partition_change_vs_initial") or {}).get("partition_assignment_changed_count")
                if timing is not None and abs(timing - float(cells[seed]["tns_ns"])) < 1e-6 and count == int(cells[seed]["assignment_changed_count"]):
                    audit["visible"][seed] = {"body_path": path + ".cells", "tns_ns": timing,
                                              "instances_changed_vs_official_initial": count}
        if audit["visible"] and set(audit["visible"]) == set(cells):
            audit["status"] = "all_observed_bp_seed_fields_in_recorded_main_request"
        return audit
    return {"status": "unknown_no_recorded_main_request_body", "member": member}


def compare(bundle, arm, old, new):
    flags, evidence = [], {}
    for seed in sorted(new):
        if seed not in old:
            continue
        parent, child = old[seed], new[seed]
        if str(parent["valid"]).lower() != "true" or str(child["valid"]).lower() != "true":
            evidence[seed] = {"status": "unverified_or_invalid"}
            flags.append(None)
            continue
        totals = [json.loads(bundle.read(arm + "/" + sample["raw_receipt"]))["metrics"]["instance_count"]
                  for sample in (parent, child)]
        if totals[0] != totals[1]:
            raise ValueError("Different instance population for a matching case/seed")
        count = totals[0]
        before, after = (int(sample["assignment_changed_count"]) for sample in (parent, child))
        lower = min(abs(before - after), abs(before + after - count))
        certified_no_movement_mod_flip = before in (0, count) and after in (0, count)
        delta = float(child["tns_ns"]) - float(parent["tns_ns"])
        effect = False if delta <= 1e-6 or certified_no_movement_mod_flip else (True if lower > 0 else None)
        flags.append(effect)
        evidence[seed] = {"tns_delta_ns": round(delta, 6), "changed_vs_frozen_initial": [before, after],
                          "instance_count": count, "parent_child_nonflip_changes_lower_bound": lower,
                          "both_improvements_certified": effect}
    all_three = ("not_observed_on_all_three" if set(new) != {"1001", "1002", "1003"} or len(flags) != 3 else
                 ("no" if False in flags else "yes" if all(v is True for v in flags) else "unknown"))
    return {"all_three": all_three, "by_seed": evidence}


def audit(bundle, arm):
    rows = list(csv.DictReader(io.StringIO(bundle.read(arm + "/training-cells.csv").decode("utf-8-sig"))))
    members = sorted(n for n in bundle.namelist() if n.startswith(arm + "/rounds/round-") and n.endswith(".json"))
    prior = {}
    report = []
    for member in members:
        data = json.loads(bundle.read(member))
        request = data["request"]
        candidate = request["candidate_id"]
        number = int(data["round"])
        key = data["submitted_search_decision"].get("parent_id")
        cells = {str(row["seed"]): row for row in rows if row["case"] == "bp-ng45" and row["candidate_id"] == candidate}
        parent = prior.get(key)
        pair = compare(bundle, arm, parent[1], cells) if parent else {"all_three": "unknown_no_same_session_parent_measurement"}
        record = {"round": number, "parent_round": parent[0] if parent else None, "bp_seeds": sorted(cells),
                  "source_member": member, "pair_outcome": pair,
                  "evidence_from_this_round_in_next_main_request": next_request(bundle, arm, number, candidate, cells)}
        report.append(record)
        prior[candidate] = (number, cells)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_zip", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".json" or args.output.resolve() == args.review_zip.resolve():
        raise ValueError("Write the JSON report outside the source archive.")
    arms = ("claude-original", "ours-new", "ours-previous", "claude-new")
    with ZipFile(args.review_zip) as bundle:
        result = {name: audit(bundle, name) for name in arms}
    # The first parent normally is the published program, not a measured local rerun.
    report = {"kind": "retrospective_offline_audit", "input": args.review_zip.name,
              "archive_sha256": hashlib.sha256(args.review_zip.read_bytes()).hexdigest(),
              "method": [
                  "Only actual earlier evaluated parents within the same recorded session count; frozen published measurements do not substitute for local measurements.",
                  "For the same case, seed, instances and binary frozen reference: if parent/child distances to that reference are a/b of N, min(abs(a-b),abs(a+b-N)) lower-bounds parent-child distance even after an optional whole-tier flip. Positive certifies local changes; zero alone does not prove unchanged.",
                  "Success per seed requires non-flip change and positive final TNS delta over 1e-6 ns. One physical observation per seed; neither independent reruns nor a causal effect of feedback were measured.",
                  "Visibility means seed-indexed actual TNS and changed instance count vs frozen initial for that exact candidate in the first logged main generation request of the next round. Ignore planning, review, alternative requests and templates; check for matching response. Absence of this structured match does not prove no aggregate or textual feedback.",
                  "claude-new is a diagnostic panel with one bp seed (1002) per round. Do not compare it as a three-seed bp evaluation."],
              "runs": result}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for arm, records in result.items():
        print(arm, [(r["round"], r["parent_round"], r["pair_outcome"]["all_three"]) for r in records])


if __name__ == "__main__":
    main()
