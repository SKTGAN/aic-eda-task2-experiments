"""Assemble the English Claude audit without shipping credentials or deployment state."""

from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from zipfile import ZIP_DEFLATED, ZipFile


HERE = Path(__file__).resolve().parent
EXPORTS = HERE.parent
PROJECT = HERE.parents[1]
PREVIOUS = EXPORTS / "2026-11-18-claude-review"
OVERNIGHT = EXPORTS / "2026-11-18-overnight"
sys.path.insert(0, str(PREVIOUS))
from build_english_review import english


AGENT = "AgenticBench/agent/loss_decoder"
OUT = HERE / "claude-harness-self-test-ablation-audit-en.zip"
HAN = re.compile(r"[\u3400-\u9fff]")
SECRET = re.compile(r"(?i)\bBearer\s+[a-z0-9_.+=/-]{15,}|\bsk-[a-z0-9_-]{15,}")


def digest(body):
    return sha256(body.encode("utf-8")).hexdigest()


def assemble(z):
    provenance = {}

    def add(name, body):
        if isinstance(body, bytes):
            body = body.decode("utf-8-sig")
        translated = english(body, name)
        assert not HAN.search(translated) and not SECRET.search(translated), name
        if name.endswith(".py"):
            compile(translated, name, "exec")
        if body != translated:
            provenance[name] = {"source_sha256": digest(body), "review_sha256": digest(translated)}
        z.writestr(name, translated)

    def copy(name, path):
        add(name, path.read_bytes())

    for name in ("START_HERE.md", "BUNDLE_MAP.md", "RESEARCH_NOTES.md", "EXPERIMENT_PROTOCOL.md"):
        copy(name, HERE / name)
    for version, folder in (("branching", PROJECT / "harness-branching"),
                            ("two-stage", PROJECT / "harness-fourth/next-harness")):
        for p in sorted((folder / AGENT).iterdir()):
            if p.is_file() and p.suffix in {".py", ".md", ".txt"}:
                copy(f"sources/{version}/{AGENT}/{p.name}", p)
    for p in sorted((PROJECT / "harness-branching/tests").glob("test_*.py")):
        copy(f"sources/branching/tests/{p.name}", p)
    with ZipFile(OVERNIGHT / "claude-three-server-r3-15332.zip") as r3:
        for entry in r3.namelist():
            if entry.endswith((".py", ".json", ".md")):
                add(f"sources/claude-r3/{entry}", r3.read(entry))

    table = {
        "A": (PROJECT / "local-experiments/hard_negative_margin.py",
              PROJECT / "official/contest-work/bp-fe-ng45-1001-hard-negative-comparison.json"),
        "B": (PROJECT / "harness-feedback-template/experiments/flipped_layer_decoder.py",
              PROJECT / "harness-feedback-template/experiments/bp-fe-ng45-1001-flipped-comparison.json"),
        "AB": (PROJECT / "harness-feedback-template/experiments/hard_negative_flipped_decoder.py",
               PROJECT / "harness-feedback-template/experiments/bp-fe-ng45-1001-hard-negative-flipped-comparison.json"),
    }
    copy("evidence/local-factorial/check_factorial.py", HERE / "check_factorial.py")
    for factor, (source, receipt) in table.items():
        copy(f"evidence/local-factorial/{factor}.py", source)
        copy(f"evidence/local-factorial/{factor}.json", receipt)
    with ZipFile(PREVIOUS / "claude-three-server-harness-review-en.zip") as review:
        for member in review.namelist():
            if member.startswith("context/previous-review/official/"):
                named = member.removeprefix("context/previous-review/official/")
                if not member.endswith("/"):
                    add("reference/" + named, review.read(member))
                continue
            if member == "run-index.json":
                add("evidence/runs/run-index.json", review.read(member))
                continue
            if member.endswith(("/training-cells.csv", "/public-validation.json", "/RUN_SUMMARY.md",
                                "/agent.stderr", "/interactions/coverage.json")):
                add("evidence/runs/" + member, review.read(member))
                continue
            if member.startswith(("ours-new/rounds/", "claude-original/rounds/", "claude-new/rounds/")):
                add("evidence/runs/" + member, review.read(member))
                continue
            if member in {"ours-new/interactions/round-04.jsonl", "claude-new/interactions/round-03.jsonl",
                          "claude-original/programs/round-04.py", "claude-original/programs/round-06.py"}:
                add("evidence/runs/" + member, review.read(member))
    for name in ("branching-three-machine-replay.json", "claude-formal-vs-official-reference.json"):
        copy("evidence/runs/" + name, OVERNIGHT / name)
    for name in ("uniform-control-bp_fe-ng45-1003.json", "critical-positives-bp_fe-ng45-1003.json"):
        copy("evidence/local-factorial/" + name, EXPORTS / "2026-11-17-local-followup" / name)
    z.writestr("SOURCE_PROVENANCE.json", json.dumps(provenance, indent=2) + "\n")


def main():
    with ZipFile(OUT, "w", compression=ZIP_DEFLATED, compresslevel=6) as z:
        assemble(z)
    with ZipFile(OUT) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names))
        for p in ("START_HERE.md", "evidence/local-factorial/AB.json", "reference/TASK_BRIEF.md",
                  "sources/branching/" + AGENT + "/decision_evidence.py"):
            assert p in names, p
        assert sum(n.startswith("evidence/runs/claude-original/rounds/") for n in names) == 10
        print(str(OUT))
        print(f"{len(names)} files; {OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
