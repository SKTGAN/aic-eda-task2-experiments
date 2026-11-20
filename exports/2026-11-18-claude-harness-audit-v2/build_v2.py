"""Repackage the prior audit evidence with the rolling-ablation review."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / "2026-11-18-claude-harness-audit" / "claude-harness-self-test-ablation-audit-en.zip"
OUT = HERE / "claude-rolling-ablation-and-self-test-audit-en.zip"
REPLACED = {"START_HERE.md", "EXPERIMENT_PROTOCOL.md", "BUNDLE_MAP.md"}
DOCUMENTS = ("START_HERE.md", "ROLLING_PROTOCOL.md", "BUNDLE_MAP.md", "CLAUDE_PROMPT.txt")
EXAMPLE = "evidence/rolling-audit/rolling_example.py"
OUTPUT = "evidence/rolling-audit/example-output.json"
FIXTURES = (
    EXAMPLE,
    "evidence/runs/ours-new/rounds/round-03.json",
    "evidence/runs/ours-new/rounds/round-04.json",
    *("evidence/local-factorial/" + f for f in (
        "A.py", "B.py", "AB.py", "A.json", "B.json", "AB.json", "check_factorial.py"
    )),
)


def main():
    with ZipFile(PRIOR) as prior, ZipFile(OUT, "w", compression=ZIP_DEFLATED, compresslevel=6) as out:
        assert prior.testzip() is None
        for name in prior.namelist():
            if name not in REPLACED:
                out.writestr(name, prior.read(name))
        for doc in DOCUMENTS:
            out.write(HERE / doc, doc)
        out.write(HERE / "rolling_example.py", EXAMPLE)

    with TemporaryDirectory(dir=str(HERE)) as folder, ZipFile(OUT) as out:
        for f in FIXTURES:
            out.extract(f, folder)
        report = subprocess.check_output(
            [sys.executable, "-B", str(Path(folder) / EXAMPLE)], text=True
        )
        parsed = json.loads(report)
        assert parsed["interaction_score_points"] < -58.9
        removals = parsed["measured_removals_from_AB"]
        assert all(x["status"] == "measured" and x["conditional_score_effect"] < 0
                   for x in removals.values())
        pending = parsed["if_the_measured_B_receipt_had_been_missing"]["A"]
        assert pending["status"] == "missing_control" and pending["conditional_score_effect"] is None
        cells = parsed["nine_cell_observed_parent_vs_child"]
        assert cells["example_weak_target"]["score_delta"] > 16
        assert all(x["score_delta"] < 0 for x in cells["example_protected_cells"])
    with ZipFile(OUT, "a", compression=ZIP_DEFLATED, compresslevel=6) as out:
        out.writestr(OUTPUT, report)

    with ZipFile(OUT) as out:
        names = out.namelist()
        assert out.testzip() is None and len(names) == len(set(names))
        assert REPLACED.intersection(names) == {"START_HERE.md", "BUNDLE_MAP.md"}
        assert all(f in names for f in (*DOCUMENTS, "RESEARCH_NOTES.md", EXAMPLE, OUTPUT))
        print(str(OUT))
        print("{} files; {:.1f} KiB; rolling example verified under Python {}".format(
            len(names), OUT.stat().st_size / 1024, sys.version.split()[0]
        ))


if __name__ == "__main__":
    main()
