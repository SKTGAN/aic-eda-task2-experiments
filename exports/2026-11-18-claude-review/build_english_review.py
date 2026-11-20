"""Build a shareable English Harness review from captured evaluation evidence."""

import base64
from collections import Counter, defaultdict
import csv
from datetime import datetime
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile


HERE = Path(__file__).resolve().parent
EXPORTS = HERE.parent
PROJECT = HERE.parents[1]
AGENT = "participant-agent/loss_decoder/"
PREVIOUS = EXPORTS / "2026-11-17-handoff"
OVERNIGHT = EXPORTS / "2026-11-18-overnight"
OUTPUT = HERE / "claude-three-server-harness-review-en.zip"
ORIGINAL_REFERENCE = 20.4251
RUNS = {
    "claude-original": ("Claude original revision", 15332, "Formal training, 3 designs x 3 seeds"),
    "claude-new": ("Claude newer Harness", 27528, "Diagnostic panel, 3 designs x seed 1002"),
    "ours-new": ("Our evidence-driven Harness", 10820, "Formal training, 3 designs x 3 seeds"),
    "ours-previous": ("Our previous comparison Harness", 27528, "Formal training, 3 designs x 3 seeds"),
}
TRANSLATIONS = {
    "## 离线专家知识": "## Offline Expert Knowledge",
    "二维时序特征可作线索，三维跨层连接和合法化会改变关键路径。兼顾多个端点的违例与最差路径，通过最终时序核验切分。留意面积或宏块修复是否抵消改动。若跨层线网减少却未改善时序，应重新审视代理指标。一次检验一个主要假设，并用不同种子的结果判断收益是否稳定。":
        "2D timing features are clues; inter-die links and legalization can change critical paths. Consider violations across endpoints and the worst path, and verify the partition with final timing. Check whether area or macro repair cancels the change. If fewer inter-die nets do not improve timing, reconsider the proxy. Test one main hypothesis at a time and compare seeds.",
    "层归属不同，切割量接近也可能产生不同的时序。两项改动分别有效时，组合效果仍需独立验证。":
        "Different die assignments can have similar cut counts and different timing. Even if two changes work separately, test their combination.",
    "少数组的大幅改善可能掩盖其他退步。层归属相同而时序变化时，先用同机起点复核。":
        "Large gains on a few cells can conceal regressions. If timing changes despite an identical die assignment, first rerun the starting program on the same host.",
    "损失函数的改动只有在面积约束修复后仍改变层归属，才可能影响物理时序。新增项要和原目标量级相称，确认吸引项确实让相连单元靠近。区分上下层整体互换和面积边界附近的实例移动。切割线网减少不保证时序改善。同一算例和种子应配对比较。层归属完全相同时，先在同机复测起点。若收益集中于单个算例或种子，须验证能否复现，再决定是否沿此候选继续优化。":
        "A loss change can affect physical timing if it still changes die assignments after area repair. Match the scale of added terms to the original objective, and verify that attraction brings connected cells closer. Distinguish a full die swap from moves near the area cutoff. Fewer cut nets do not guarantee better timing. Pair comparisons by design and seed. If assignments are identical, rerun the starting program on the same host. If gains are confined to one design or seed, test reproducibility before refining the candidate.",
    "二维时序只作线索，跨层连接与合法化会改变关键路径。损失变化若不改变面积截点附近的排序，最终分层可能不动。整体翻转与局部边界重排分开统计，翻转仍可能改变时序。观察最差路径和多个端点的违例，按同算例同种子比较。层归属相同而时序差异明显时，先做同机对照再归因。割网下降未必改善时序。一次检验一个分层假设，并用多个种子核验收益；少数高分可能掩盖普遍退步。":
        "Use 2D timing as a clue; inter-die connections and legalization can change critical paths. If a loss change does not alter ordering near the area cutoff, the final die assignment may be unchanged. Measure full die swaps separately from local boundary moves; a swap can still change timing. Track the worst path and violations across endpoints, comparing the same design and seed. If identical assignments produce materially different timing, rerun a same-host control before attributing the difference. Fewer cut nets do not guarantee better timing. Test one partition hypothesis at a time and verify gains across seeds, since a few high scores can mask widespread regressions.",
}
HAN = re.compile(r"[\u3400-\u9fff]")
PORTAL_IP = re.compile(r"\b(?:223\.109\.239\.|180\.127\.11\.)\d{1,3}\b")


def english(text, name):
    for source, target in TRANSLATIONS.items():
        for spelling in (source, json.dumps(source, ensure_ascii=True)[1:-1]):
            text = text.replace(spelling, target)
    text = PORTAL_IP.sub("[SERVER-IP-REDACTED]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED]", text)
    text = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9_.+=/-]{12,}", "Bearer [REDACTED]", text)
    match = HAN.search(text)
    if match:
        raise ValueError("Untranslated text in " + name + ": " + text[match.start():match.start()+140])
    return text


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def csv_text(fields, rows):
    s = io.StringIO()
    writer = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return s.getvalue()


def points(value):
    return "—" if value is None else f"{value:.2f}"


def log_events(data):
    return [json.loads(line) for line in data.splitlines() if line.strip()]


def partition_events(events):
    groups = defaultdict(list)
    current = 1
    for event in events:
        kind = event["event"]
        target = max(1, current - 1) if kind in {"incumbent", "selected", "budget_stop"} else current
        groups[target].append(event)
        if kind == "evaluated":
            current += 1
    return groups


def archive_capture(name):
    p = HERE / "captures" / (name + ".b64")
    z = ZipFile(io.BytesIO(base64.b64decode(p.read_bytes())))
    assert z.testzip() is None, p
    return z


def request_rows(files, events):
    ledger = json.loads(files["ledger.json"])
    if ledger.get("evaluations"):
        return ledger["evaluations"]
    receipts = {e["request_id"]: e for e in events if e.get("event") == "evaluated"}
    rows = []
    for event in events:
        if event["event"] != "submitted":
            continue
        rid = event["request_id"]
        feedback = receipts.get(rid, {})
        if not feedback:
            fallback = files.get("receipts/" + rid + ".json")
            feedback = json.loads(fallback) if fallback else {}
        rows.append({key: feedback.get(key) for key in ("candidate_id", "status")} | {"request_id": rid})
    return rows


def assignment_metrics(metrics):
    fields = {
        "wns_ns": "final_global_wns_setup_ns",
        "tns_ns": "final_global_tns_setup_ns",
        "cut_nets": "cut_net_count",
        "weighted_cut": "timing_weighted_cut",
        "assignment_changed_count": "partition_assignment_changed_count",
        "assignment_changed_fraction": "partition_assignment_changed_fraction",
        "assignment_identical": "partition_assignment_identical",
        "area_balance_error": "area_balance_error",
    }
    return {k: metrics.get(a) for k, a in fields.items()}


def collect_cells(files, root, result, expected):
    matrix = (result.get("metrics") or {}).get("matrix") or {}
    compiled = matrix.get("cells") or []
    if not compiled:
        compiled = []
        for name, body in files.items():
            if not (name.startswith(root + "/cells/") and name.endswith("/result/evaluation_result.json")):
                continue
            case, seed = name.split("/")[-4:-2]
            compiled.append({"case": case, "seed": seed, "status": "physical-receipt-only",
                             "metrics": json.loads(body).get("metrics") or {}})
    rows = []
    for row in compiled:
        case, seed = row["case"], row["seed"]
        stem = f"{root}/cells/{case}/{seed}"
        raw = f"{stem}/result/evaluation_result.json"
        physical = json.loads(files.get(raw, "{}")).get("metrics") or {}
        metrics = (row.get("metrics") or {}) | {k: v for k, v in physical.items() if k not in (row.get("metrics") or {})}
        phase = {}
        for stage in ("frontend", "backend"):
            path = f"{stem}/container/execution/{stage}/terminal.json"
            terminal = json.loads(files.get(path, "{}"))
            phase[f"{stage}_exit"] = terminal.get("exit_code")
            phase[f"{stage}_sec"] = terminal.get("wall_seconds")
        rows.append({
            "case": case, "seed": seed, "status": row.get("status"), "score": row.get("score"),
            "raw_score": row.get("raw_score"), "valid": row.get("valid"),
            **assignment_metrics(metrics), **phase,
            "raw_receipt": "raw/" + raw if raw in files else None,
        })
    return rows, matrix, matrix.get("expected_cells", expected)


def source_from(candidate):
    for key, value in candidate.get("candidate_files", {}).items():
        if key == "loss_decoder_program.json" and isinstance(value, dict):
            return value.get("source")
    return candidate.get("source")


def run_review(label, files, before_translation, host, dest):
    title, port, scope = RUNS[label]
    events = log_events(files[AGENT + "search.jsonl"])
    counts = Counter(event["event"] for event in events)
    by_round = partition_events(events)
    submitted = {r["request_id"]: r for r in events if r["event"] == "submitted"}
    evaluated = {r["request_id"]: r for r in events if r["event"] == "evaluated"}
    requests = request_rows(files, events)
    expected = 3 if label == "claude-new" else 9

    def write(path, data):
        dest.writestr(f"{label}/{path}", data)

    for name, body in files.items():
        if name != AGENT + "search.jsonl" and not (name.startswith(AGENT) and name.endswith((".py", ".md", ".txt"))):
            write("raw/" + name, body)
    write("interactions/all-rounds.jsonl", files[AGENT + "search.jsonl"])
    write("host.json", encode(host))
    write("interactions/coverage.json", encode({
        "evaluations_submitted": len(requests),
        "feedback_events_written": counts["evaluated"],
        "recorded_requests_with_body": counts["model_request"],
        "recorded_visible_responses": counts["model_response"],
        "event_types": dict(counts),
        "exact_model_bodies_absent_for_this_run": label == "claude-original",
    }))
    provenance = {}
    harness = {}
    for name, body in files.items():
        if name.startswith(AGENT) and name.endswith((".py", ".md", ".txt")):
            short = name.removeprefix(AGENT)
            if name.endswith(".py"):
                compile(body, name, "exec")
            path = "AgenticBench/agent/loss_decoder/" + short
            raw = before_translation[name]
            modified = body != raw
            provenance[path] = {"sha256_captured_before_translation": sha256(raw.encode()).hexdigest(),
                                "sha256_english_review_copy": sha256(body.encode()).hexdigest(),
                                "translated_for_review": modified}
            harness[path] = body
            write("harness/" + path, body)
    harness["SOURCE_PROVENANCE.json"] = encode(provenance)
    if label == "claude-new":
        with ZipFile(PREVIOUS / "claude-overnight-27528-zh.zip") as launch:
            driver = "development/diagnose_harness.py"
            body = english(launch.read(driver).decode("utf-8-sig"), driver)
            harness[driver] = body
    harness["README.md"] = (
        f"# {title}\n\nSSH port in the original run inventory: {port}.\n\n"
        f"{scope}.\n\n"
        "Agent files were captured from the host's participant-agent directory. English wording "
        "and matching prompt section labels were translated where applicable. SOURCE_PROVENANCE.json "
        "records hashes before and after translation. Candidate implementations are in the main review ZIP.\n"
    )
    write("harness/SOURCE_PROVENANCE.json", harness["SOURCE_PROVENANCE.json"])
    outdir = HERE / "harness-packages"
    outdir.mkdir(exist_ok=True)
    single = outdir / (label + "-harness-en.zip")
    packet = io.BytesIO()
    with ZipFile(packet, "w", compression=ZIP_DEFLATED) as z:
        for path, body in harness.items():
            z.writestr(path, body)
    write("harness-package-en.zip", packet.getvalue())
    single.write_bytes(packet.getvalue())

    collected = []
    csv_rows = []
    for number, row in enumerate(requests, 1):
        rid, cid = row["request_id"], row["candidate_id"]
        label_round = f"round-{number:02}"
        candidate = json.loads(files.get(f"candidates/{cid}/candidate.json", "{}"))
        source = source_from(candidate)
        if not source:
            raise ValueError(f"Missing candidate source in {label}, evaluation {number}")
        compile(source, f"{label}/{label_round}", "exec")
        program = f"programs/{label_round}.py"
        write(program, source)
        root = "evaluations/" + rid
        result = json.loads(files.get(root + "/evaluation_result.json", "{}"))
        cells, matrix, expected_cells = collect_cells(files, root, result, expected)
        feedback = evaluated.get(rid)
        bridge_file = "receipts/" + rid + ".json"
        diagnostic_bridge = json.loads(files.get(bridge_file, "{}"))
        decision = submitted.get(rid, {})
        score = (result.get("metrics") or {}).get("combined_score")
        duration = None
        if row.get("accepted_at") and row.get("completed_at"):
            duration = (datetime.fromisoformat(row["completed_at"])
                        - datetime.fromisoformat(row["accepted_at"])).total_seconds()
        group = by_round.get(number, [])
        write(f"interactions/{label_round}.jsonl", "".join(
            json.dumps(item, ensure_ascii=False) + "\n" for item in group
        ))
        part = {
            "round": number, "request": row, "program": program, "program_sha256": sha256(source.encode()).hexdigest(),
            "submitted_search_decision": decision or None,
            "recorded_harness_feedback": feedback,
            "diagnostic_bridge_feedback": diagnostic_bridge.get("feedback"),
            "evaluator_receipt": "raw/" + root + "/evaluation_result.json" if result else None,
            "score": score, "expected_cells": expected_cells, "finished_cells": len(cells),
            "elapsed_seconds": duration, "case_summaries": matrix.get("cases"),
            "physical_cells": cells,
            "saved_requests_in_this_round": sum(x["event"] == "model_request" for x in group),
            "saved_responses_in_this_round": sum(x["event"] == "model_response" for x in group),
        }
        write("rounds/" + label_round + ".json", encode(part))
        collected.append(part)
        csv_rows.extend({"round": number, "candidate_id": cid, **cell} for cell in cells)
    fields = ["round", "candidate_id", "case", "seed", "status", "score", "raw_score", "valid",
              *assignment_metrics({}), "frontend_exit", "frontend_sec", "backend_exit", "backend_sec", "raw_receipt"]
    write("training-cells.csv", csv_text(fields, csv_rows))

    validation = []
    for name, body in files.items():
        if not name.startswith("validate/") or not name.endswith("/evaluation_result.json") or name.count("/") != 2:
            continue
        score_record = json.loads(body)
        fold, matrix, n = collect_cells(files, name.rsplit("/", 1)[0], score_record, 6)
        validation_score = (score_record.get("metrics") or {}).get("combined_score")
        validation.append({"candidate_id": name.split("/")[1], "score": validation_score, "expected_cells": n,
                           "case_summaries": matrix.get("cases"), "physical_cells": fold})
        if fold:
            write("public-validation-cells.csv", csv_text(fields[2:], fold))
    if validation:
        write("public-validation.json", encode(validation))

    best = max((x for x in collected if x["score"] is not None), key=lambda x: x["score"])
    recorded = len([x for x in collected if x["recorded_harness_feedback"]])
    table = [
        f"# {title}", "", f"**Server SSH port {port} · {scope}.**", "",
        f"Best complete score **{best['score']:.2f}** at round {best['round']}. "
        f"{len(collected)} submissions, {recorded} Harness feedback events, {counts['model_request']} saved model requests "
        f"and {counts['model_response']} saved visible replies.", "",
        "| Round | Evaluator score | Cells with receipts | Decision | Minutes | Candidate ID prefix |",
        "|---:|---:|---:|---|---:|---|",
    ]
    for x in collected:
        decision = (x["submitted_search_decision"] or {}).get("decision") or {}
        minutes = None if x["elapsed_seconds"] is None else x["elapsed_seconds"] / 60
        table.append(f"| {x['round']} | {points(x['score'])} | {x['finished_cells']}/{x['expected_cells']} | "
                     f"{decision.get('reason','—')} | {points(minutes)} | {x['request']['candidate_id'][:12]} |")
    if validation:
        table.extend(["", f"Public validation for the selected candidate completed "
                     f"**{len(validation[0]['physical_cells'])}/{validation[0]['expected_cells']}** cells with "
                     f"a score of **{validation[0]['score']:.2f}**."])
    if label == "claude-original":
        table.extend(["", "The original run logged decisions, reviews, evaluator feedback and API usage. "
                      "The full model request and reply bodies were not captured by that Harness. "
                      "The static prompts and all available feedback events are preserved."])
    if label == "ours-new":
        table.extend(["", "The evaluator completed round 4. The Harness then crashed while comparing "
                      "assignment bitsets using `int.bit_count()` in the Python 3.8 container. "
                      "Its round-4 evaluator receipt survives; the interactive feedback event was never written."])
    if label == "claude-new":
        table.extend(["", "This experiment used a three-cell diagnostic panel. The results have a different "
                      "coverage from the full nine-cell training matrix. The exact bridge model transcript "
                      "is also available in `raw/diagnostic-model.jsonl`."])
    table.extend(["", "Read `rounds/` for candidate lineage and feedback, `interactions/` for saved input and output, "
                   "`programs/` for candidate code, `training-cells.csv` for physical metrics and durations, "
                   "and `raw/` for the underlying records.", ""])
    write("RUN_SUMMARY.md", "\n".join(table))
    return {"rounds": collected, "best": best, "validation": validation, "events": dict(counts)}


def main():
    parts = {
        "claude-original": "claude-original",
        "claude-new": "claude-new-and-ours-previous",
        "ours-new": "ours-new-with-agent-logs",
        "ours-previous": "claude-new-and-ours-previous",
    }
    results = {}
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=6) as dest:
        for label, capture in parts.items():
            with archive_capture(capture) as z:
                prefix = label + "/"
                raw = {n.removeprefix(prefix): z.read(n).decode("utf-8-sig")
                       for n in z.namelist() if n.startswith(prefix)}
                translated = {n: english(body, prefix + n) for n, body in raw.items()}
                results[label] = run_review(label, translated, raw, json.loads(z.read("host.json")), dest)
        with ZipFile(PREVIOUS / "claude-two-server-harness-review-en.zip") as old:
            for member in old.namelist():
                if member.startswith(("official/", "historical/")) or member in {
                        "RUN_OVERVIEW.md", "LOCAL_EXPERIMENTS.md", "THREE_DAY_PLAN.md", "REVIEW_REQUEST.md"}:
                    dest.writestr("context/previous-review/" + member, english(old.read(member).decode("utf-8-sig"), member))
        for file in sorted((EXPORTS / "2026-11-17-local-followup").glob("*.json")):
            dest.writestr("context/local-followup/" + file.name, english(file.read_text(encoding="utf-8"), file.name))
        p = OVERNIGHT / "claude-formal-vs-official-reference.json"
        if p.is_file():
            dest.writestr("context/" + p.name, english(p.read_text(encoding="utf-8-sig"), p.name))
        readme = (HERE / "REVIEW_BRIEF.md").read_text(encoding="utf-8")
        dest.writestr("START_HERE.md", english(readme, "START_HERE.md"))
        dest.writestr("run-index.json", encode({
            label: {
                "ssh_port": RUNS[label][1], "evaluation_scope": RUNS[label][2],
                "candidate_count": len(data["rounds"]), "full_scores": [r["score"] for r in data["rounds"]],
                "best_round": data["best"]["round"], "best_score": data["best"]["score"],
                "events": data["events"], "public_validation_scores": [x["score"] for x in data["validation"]],
            } for label, data in results.items()
        }))

    with ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        for label, count in {"claude-original": 10, "claude-new": 3, "ours-new": 4, "ours-previous": 5}.items():
            assert sum(p.startswith(f"{label}/programs/") for p in z.namelist()) == count, label
            with ZipFile(io.BytesIO(z.read(label + "/harness-package-en.zip"))) as h:
                assert h.testzip() is None
        assert len(results["claude-original"]["validation"][0]["physical_cells"]) == 6
        assert sum(len(x["physical_cells"]) for x in results["claude-original"]["rounds"]) == 90
        assert any(n.startswith("ours-new/") and n.endswith("/agent.stderr")
                   and b"bit_count" in z.read(n) for n in z.namelist())
    print(OUTPUT)
    print(f"{OUTPUT.stat().st_size:,} bytes · 22 candidate programs · {len(z.namelist())} files")


if __name__ == "__main__":
    main()
