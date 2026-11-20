"""Stream a read-only contest run snapshot to stdout on the evaluation host."""

import base64
from datetime import datetime
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile


STAGE_LOGS = {"stage.log", "backend-stage.log", "container.log", "run.log", "opt.log",
              "assignment.log", "assembly_sta.log"}
KEYS = re.compile(r"(?i)^(api[_-]?key|provider[_-]?key|access[_-]?token|authorization|"
                  r"password|secret|cookie|token|reasoning_content|reasoning_text)$")


def scrub(text):
    text = re.sub(r"\bsk-[a-zA-Z0-9_-]{12,}", "[REDACTED]", text)
    text = re.sub(r"(?i)\bBearer\s+[a-z0-9_.+=/-]{12,}", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)(\b(password|provider_key|api_key|access_token)\s*[=:]\s*)"
                  r"[^\s,;\"]+", r"\1[REDACTED]", text)
    return text


def sanitize(value):
    if isinstance(value, dict):
        return {key: sanitize(v) for key, v in value.items() if not KEYS.fullmatch(key)}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return scrub(value) if isinstance(value, str) else value


def as_json(value):
    return json.dumps(sanitize(value), ensure_ascii=False, indent=2) + "\n"


def budget(work):
    path = work / "control" / "budget.sqlite"
    if not path.is_file():
        return {}
    fields = {
        "evaluations": ("request_id", "candidate_id", "status", "accepted_at", "completed_at", "result_hash"),
        "model_calls": ("request_id", "model", "status", "created_at", "accepted_at", "settled_at",
                        "completed_at", "input_tokens", "output_tokens", "cost_rmb", "cache_hit_tokens",
                        "reserved_cost_rmb", "error_type"),
    }
    result = {}
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=6) as connection:
        connection.row_factory = sqlite3.Row
        for table, desired in fields.items():
            available = {row[1] for row in connection.execute("pragma table_info(" + table + ")")}
            columns = [name for name in desired if name in available]
            if columns:
                query = "select " + ",".join(columns) + " from " + table
                query += " order by " + next((k for k in ("accepted_at", "created_at") if k in columns), "rowid")
                result[table] = [dict(row) for row in connection.execute(query)]
    return result


def write_file(archive, path, name, *, tail_max=0):
    if not path.is_file() or path.is_symlink():
        return None
    size = path.stat().st_size
    if size > 12_000_000 and not tail_max:
        return {"omitted": name, "bytes": size}
    with path.open("rb") as stream:
        if tail_max and size > tail_max:
            stream.seek(size - tail_max)
        data = stream.read()
    text = data.decode("utf-8-sig", errors="replace")
    if path.suffix == ".json":
        text = as_json(json.loads(text))
    elif path.suffix == ".jsonl":
        records = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.dumps(sanitize(json.loads(line)), ensure_ascii=False))
            except ValueError:
                continue
        text = "\n".join(records) + "\n"
    else:
        text = scrub(text)
    truncated = bool(tail_max and size > tail_max)
    if truncated:
        text = "[Tail excerpt. Original size: {} bytes.]\n".format(size) + text
    archive.writestr(name, text)
    return {"path": name, "captured_bytes": len(data), "source_bytes": size,
            "captured_sha256": sha256(data).hexdigest(), "tail_excerpt": truncated}


def capture(archive, label, work):
    if not work.is_dir():
        raise FileNotFoundError(work)
    entries = []
    seen = set()

    def add(file, relative, *, tail_max=0):
        name = label + "/" + relative
        if name in seen:
            return
        seen.add(name)
        try:
            entry = write_file(archive, file, name, tail_max=tail_max)
            if entry:
                entries.append(entry)
        except (OSError, ValueError) as exc:
            entries.append({"omitted": name, "reason": type(exc).__name__})

    def take(relative, *, tail_max=0):
        add(work / relative, relative, tail_max=tail_max)

    for name in ("session-result.json", "diagnostic-result.json", "DIAGNOSTIC_ONLY.json",
                 "diagnostic-model.jsonl", "panel.json", "control/session-start.json",
                 "control/model-gateway.log"):
        take(name)
    for name in ("runner.log", "check.log", "after-training/pipeline.log", "after-training/public-validation.log"):
        add(work.parent / name, "host-logs/" + name)
    for agent in (work / "participant-agent" / "loss_decoder",):
        if agent.is_dir():
            for file in sorted(agent.iterdir()):
                if file.suffix in {".py", ".md", ".txt", ".jsonl", ".json"}:
                    add(file, file.relative_to(work).as_posix())
    for name in ("candidates/*/candidate.json", "receipts/*.json", "control/*.stderr",
                 "control/*.stdout", "control/**/agent.stderr", "control/**/agent.stdout",
                 "agent-logs/**/agent.stderr", "agent-logs/**/agent.stdout",
                 "agent.stderr", "agent.stdout"):
        for file in sorted(work.glob(name)):
            take(file.relative_to(work).as_posix())
    for prefix in ("evaluations", "validate", "baseline", "qualification"):
        root = work / prefix
        if not root.is_dir():
            continue
        for file in sorted(root.glob("*/*")):
            if file.is_file() and file.name in {"evaluation_result.json", "matrix.json", "diagnostics.json"}:
                take(file.relative_to(work).as_posix())
        for name in ("evaluation_result.json", "matrix.json"):
            take(prefix + "/" + name)
        for file in sorted(root.glob("*/cells/*/*/result/evaluation_result.json")):
            take(file.relative_to(work).as_posix())
        for cell in sorted(root.glob("*/cells/*/*")):
            for pattern in ("*.json", "result/*.json", "result/*.log", "container/execution/*/*.json",
                            "container/execution/*/*.log", "result/run/*/*.log"):
                for file in sorted(cell.glob(pattern)):
                    if file.suffix == ".json":
                        if file.stat().st_size <= 2_000_000 and file.name not in {
                                "partition_assignment.json", "placement.json", "graph.json"}:
                            take(file.relative_to(work).as_posix())
                    elif file.name in STAGE_LOGS:
                        take(file.relative_to(work).as_posix(), tail_max=24_000)
    for name in ("agent.stderr", "agent.stdout"):
        for file in sorted(work.rglob(name)):
            take(file.relative_to(work).as_posix())
    try:
        ledger = budget(work)
    except sqlite3.Error as exc:
        ledger = {"unavailable": str(exc)}
    archive.writestr(label + "/ledger.json", as_json(ledger))
    archive.writestr(label + "/capture-index.json", as_json({
        "captured_at": datetime.now().astimezone().isoformat(),
        "files": entries,
        "scope": "Harness source, evaluation requests and receipts, interaction events, and bounded physical stage logs.",
    }))


def main():
    data = io.BytesIO()
    with ZipFile(data, "w", compression=ZIP_DEFLATED, compresslevel=5) as archive:
        for instance in sys.argv[1:]:
            label, location = instance.split("=", 1)
            capture(archive, label, Path(location))
        proc = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                               "--format=csv,noheader"], capture_output=True, text=True, timeout=8)
        archive.writestr("host.json", as_json({"gpu": proc.stdout.strip(),
                                              "captured_at": datetime.now().astimezone().isoformat()}))
    sys.stdout.buffer.write(base64.b64encode(data.getvalue()) + b"\n")


if __name__ == "__main__":
    main()
