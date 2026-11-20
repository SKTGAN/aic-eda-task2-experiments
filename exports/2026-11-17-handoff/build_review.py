"""Build the English review archive from the two authorized read-only captures."""

import base64
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
CAPTURE = HERE.parent / "2026-11-17-claude"
AGENT = "participant-agent/loss_decoder/"
OUT = {}
CHINA = timezone(timedelta(hours=8))
KNOWN = {
    "## 离线专家知识": "## Offline Expert Knowledge",
    "二维时序特征可作线索，三维跨层连接和合法化会改变关键路径。兼顾多个端点的违例与最差路径，通过最终时序核验切分。留意面积或宏块修复是否抵消改动。若跨层线网减少却未改善时序，应重新审视代理指标。一次检验一个主要假设，并用不同种子的结果判断收益是否稳定。":
        "2D timing features are clues; inter-die links and legalization can change critical paths. Account for violations across endpoints and the worst path, and verify the partition with final timing. Check if area or macro repair cancels the change. If inter-die nets decrease without a timing gain, reconsider the proxy. Test one main hypothesis at a time and compare seeds.",
    "层归属不同，切割量接近也可能产生不同的时序。两项改动分别有效时，组合效果仍需独立验证。":
        "Different die assignments can have similar cuts and different timing. Even if two changes work separately, test the combination.",
    "少数组的大幅改善可能掩盖其他退步。层归属相同而时序变化时，先用同机起点复核。":
        "Large gains on a few cells can conceal regressions. If die assignments match but timing changes, first rerun the starting program on the same host.",
}


def clean(name, body):
    for source, target in KNOWN.items():
        body = body.replace(source, target)
        for variant in (json.dumps(source, ensure_ascii=True)[1:-1],):
            body = body.replace(variant, target)
    body = re.sub(r"/home/[^/\s]+/aic-eda-task2-local", "/local-workspace", body)
    body = re.sub(r"(?i)\bBearer [A-Za-z0-9_./+=-]{16,}", "Bearer [REDACTED]", body)
    body = re.sub(r"\bsk-[A-Za-z0-9_-]{15,}", "[REDACTED]", body)
    if re.search(r"[\u3400-\u9fff]", name + body):
        raise ValueError("Untranslated text in " + name)
    return body


def add(name, body):
    if isinstance(body, bytes):
        body = body.decode("utf-8-sig")
    if name in OUT:
        raise ValueError("Duplicate archive member: " + name)
    OUT[name] = clean(name, body)


def as_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def clock(s):
    if not s:
        return "-"
    return datetime.fromisoformat(s).astimezone(CHINA).strftime("%Y-%m-%d %H:%M:%S UTC+08")


def compact(text, length=235):
    return " ".join(str(text or "").replace("|", "/").split())[:length]


def row_score(r, cases, case, seed, wns, tns):
    spec = cases.get(case, {})
    if not isinstance(wns, (float, int)) or not isinstance(tns, (float, int)) or not spec:
        return None, None
    w = spec["reference_wns_deficit_ns"]
    t = spec["reference_tns_deficit_ns"]
    raw = 100 * (0.4 * (1 - max(0, -wns)/w) + 0.6 * (1 - max(0, -tns)/t))
    pm = spec["measurements"]["loss_decoder"][seed]
    initial = max(-100, 100 * (0.4 * (1 - max(0,-pm["wns_ns"])/w) + 0.6 * (1 - max(0,-pm["tns_ns"])/t)))
    return r.get("score", max(-100, raw)), initial


def capture(arm, label, reference):
    filename = CAPTURE / f"live-{arm}-20261117.capture"
    source = io.BytesIO(base64.b64decode(filename.read_bytes()))
    with ZipFile(source) as z:
        if z.testzip() is not None:
            raise ValueError("Corrupt capture for " + arm)
        meta = json.loads(z.read("capture.json"))
        add(f"{label}/capture.json", as_json(meta))
        times = meta["evaluations"]
        trace_text = z.read(AGENT + "search.jsonl").decode()
        trace = [json.loads(line) for line in trace_text.splitlines() if line.strip()]
        add(f"{label}/interactions/all-rounds.jsonl", trace_text)
        events = Counter(r["event"] for r in trace)
        groups, decisions, receipts = defaultdict(list), {}, {}
        active_number = 1
        for event in trace:
            kind = event["event"]
            groups[max(1, active_number - 1) if kind == "incumbent" else active_number].append(event)
            if kind == "submitted":
                decisions[event["request_id"]] = event
            if kind == "evaluated":
                receipts[event["request_id"]] = event
                active_number += 1
        for number, group in sorted(groups.items()):
            add(f"{label}/interactions/round-{number:02}.jsonl",
                "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in group))
        source_hashes = {}
        for name in z.namelist():
            if name.startswith(AGENT) and not name.endswith("search.jsonl"):
                data = z.read(name)
                translated = clean(name, data.decode("utf-8-sig"))
                source_hashes[Path(name).name] = {"sha256_as_run": sha256(data).hexdigest(),
                    "translated_for_review": translated != data.decode("utf-8-sig")}
                add(f"{label}/harness/{Path(name).name}", data)
            elif name.startswith("evaluations/") or name.startswith("candidates/"):
                add(f"{label}/{name}", z.read(name))
        add(f"{label}/harness/SOURCE_PROVENANCE.json", as_json(source_hashes))
        intro = [f"## {label}", "", "Captured " + clock(meta["at"]) + ".",
                 f"{len(times)} submitted candidates; {events['evaluated']} completed feedback records.",
                 (f"{events['model_request']} recorded model requests and {events['model_response']} visible replies. "
                  "The log contains response text and available usage, not hidden reasoning.")
                 if events["model_request"] else
                 "This running Harness did not record request or reply bodies. Its full recorded decision trace, visible review verdicts, token/cost accounting, candidate source, and physical receipts are included.",
                 "", "| Round | Score or progress | Search decision | Changed function and mechanism | Minutes | Request ID prefix |",
                 "|---:|---:|---|---|---:|---|"]
        output = io.StringIO()
        csv_writer = csv.writer(output)
        csv_writer.writerow(["round","request_id","candidate_id","case","seed","status","common_score",
                             "published_initial","delta","wns_ns","tns_ns","cut_nets","weighted_cut",
                             "native_or_legacy_score","changed_instances","changed_fraction","scope"])
        for number, entry in enumerate(times, 1):
            rid = entry["request_id"]
            cid = entry.get("candidate_id")
            decision = decisions.get(rid, {})
            candidate_path = f"candidates/{cid}/candidate.json"
            body = None
            if candidate_path in z.namelist():
                body = json.loads(z.read(candidate_path))["candidate_files"]["loss_decoder_program.json"]["source"]
                compile(body, candidate_path, "exec")
                add(f"{label}/programs/round-{number:02}.py", body)
            prefix = f"evaluations/{rid}/"
            result = json.loads(z.read(prefix + "evaluation_result.json")) if prefix + "evaluation_result.json" in z.namelist() else {}
            aggregate = result.get("metrics", {})
            completed = aggregate.get("matrix", {}).get("cells") or []
            physical = [name for name in z.namelist() if name.startswith(prefix + "cells/")
                        and name.endswith("/result/evaluation_result.json")]
            if completed:
                rows = completed
            else:
                rows = [{"case": Path(p).parts[-4], "seed": Path(p).parts[-3], "status": "receipt-only",
                         "metrics": json.loads(z.read(p)).get("metrics", {})} for p in physical]
            for row in rows:
                case, seed = row["case"], str(row["seed"])
                m = row.get("metrics") or {}
                wns = m.get("final_global_wns_setup_ns")
                tns = m.get("final_global_tns_setup_ns")
                score, initial = row_score(row, reference, case, seed, wns, tns)
                csv_writer.writerow([number,rid,cid,case,seed,row.get("status"),score,initial,
                                     score-initial if score is not None and initial is not None else None,
                                     wns,tns,m.get("cut_net_count"),m.get("timing_weighted_cut"),
                                     m.get("native_paired_combined_score", m.get("combined_score")),
                                     m.get("partition_assignment_changed_count"), m.get("partition_assignment_changed_fraction"),
                                     "complete-candidate" if completed else "provisional-physical-receipt"])
            changes = "<br>".join(f"{key}: {compact(value)}" for key,value in decision.get("changed_components", {}).items())
            score = aggregate.get("combined_score")
            end = entry.get("completed_at")
            duration = (datetime.fromisoformat(end)-datetime.fromisoformat(entry["accepted_at"])).total_seconds()/60 if end else None
            intro.append(f"| {number} | {f'{score:.2f}' if score is not None else f'{len(physical)}/9 result files'} | "
                         f"{decision.get('decision',{}).get('reason','-')} | {changes or '-'} | "
                         f"{f'{duration:.1f}' if duration is not None else '-'} | {rid[:15]} |")
            add(f"{label}/rounds/round-{number:02}.json", as_json({
                "request":entry, "submit_event":decision, "feedback_event":receipts.get(rid),
                "candidate_program":f"../programs/round-{number:02}.py" if body else None,
                "physical_receipts":len(physical), "score":score,
                "source_sha256":sha256(body.encode()).hexdigest() if body else None,
            }))
        add(f"{label}/physical-cells.csv", output.getvalue())
        intro.extend(["", "See rounds/ for lineage, programs/ for the full accepted source,",
                      "physical-cells.csv for normalized timing comparisons, and evaluations/ for original receipts.",
                      "Provisional rows are not complete candidate scores.", ""])
        return "\n".join(intro)


def main():
    reference_file = PROJECT / "official/contest-source/AgenticBench/contest2/manifests/common-timing-reference.json"
    reference = json.loads(reference_file.read_bytes())["cases"]
    for name in ("REVIEW_REQUEST.md", "LOCAL_EXPERIMENTS.md"):
        add(name, (HERE/name).read_bytes())
    overview = ["# Server comparison", "",
                "Server 1 runs the Claude revision. Server 2 runs our previous optimized Harness.",
                "Published loss_decoder initial training score: 20.4251. This is not a same-host baseline.",
                "All candidates use the same official three-case, nine-cell training grid.",
                "The two snapshots were taken at different times.", "",
                capture("claude","server-1-claude",reference),
                capture("ours","server-2-local-harness",reference),
                "## Reading the English copy", "",
                "One Chinese expert heading and its three paragraphs in Server 2 were translated in the Harness and the corresponding logged prompt. Numerical results, candidate source, later prompt text, and the rest of the interaction records were retained. Original source hashes are recorded. Actual model content absent at source remains absent here.", "",
                "Candidate code and offline data in the archive are for development review. Only the declared expert section and current run evidence belong in a new competitive agent call.", ""]
    report = "\n".join(overview)
    (HERE/"RUN_OVERVIEW.md").write_text(report,encoding="utf-8",newline="\n")
    add("RUN_OVERVIEW.md", report)

    with ZipFile(PROJECT/"claude-harness-observed-review.zip") as historical:
        for name in historical.namelist():
            if name.startswith("reference/") or name.startswith("historical/") or name == "TASK_BRIEF.md":
                add("official/"+name if not name.startswith("historical/") else name, historical.read(name))
    add("official/reference/common-timing-reference.json", reference_file.read_bytes())
    for path in sorted((PROJECT/"local-experiments").glob("*.py")):
        add("local/programs/"+path.name, path.read_bytes())
    local = PROJECT/"official/contest-work"
    for path in sorted(local.iterdir()):
        if path.is_file() and (path.suffix == ".json" or path.suffix == ".log"):
            add("local/wsl/"+path.name, path.read_bytes())
    for path in sorted((PROJECT/"exports/2026-11-17-local-followup").iterdir()):
        if path.is_file() and path.suffix in (".json",".log"):
            add("local/followup/"+path.name, path.read_bytes())
    for path in sorted((HERE/"next-harness").rglob("*")):
        if path.is_file() and path.suffix in (".py",".md",".txt"):
            add(path.relative_to(HERE).as_posix(), path.read_bytes())
    for path in sorted((HERE/"development").rglob("*.py")):
        add(path.relative_to(HERE).as_posix(), path.read_bytes())
    workshop = HERE/"THREE_DAY_PLAN.md"
    if workshop.is_file():
        add(workshop.name,workshop.read_bytes())
    archive = HERE/"claude-two-server-harness-review-en.zip"
    with ZipFile(archive,"w",ZIP_DEFLATED) as z:
        for name, body in sorted(OUT.items()):
            z.writestr(name,body.encode("utf-8"))
    with ZipFile(archive) as z:
        assert z.testzip() is None
    print(archive.name,len(OUT),archive.stat().st_size)


if __name__ == "__main__":
    main()
