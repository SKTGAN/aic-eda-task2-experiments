"""Copy the matched local A/B/AB evidence into tests/fixtures/local_factorial.json.

    python3 -I tests/build_local_factorial.py /path/to/extracted/claude-rolling-ablation-and-self-test-audit-en

Development material only. Each program is checked against its recorded SHA-256 and the three
receipts against each other (same case, seed, image, memory limit and initial receipt), as the
archive's own check_factorial.py does. Nothing from the archive is executed.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

bundle = Path(sys.argv[1]).resolve()
local = bundle / "evidence" / "local-factorial"
records, programs = {}, {}
for name in ("A", "B", "AB"):
    source = (local / (name + ".py")).read_text(encoding="utf-8")
    record = json.loads((local / (name + ".json")).read_text(encoding="utf-8"))
    if sha256(source.encode()).hexdigest() != record["candidate_sha256"] or record["formal_evaluation"] is not False:
        raise ValueError(name + ": program hash or scope does not match its receipt")
    records[name], programs[name] = record, source
for key in ("case", "seed", "baseline", "image", "initial_result", "memory_limit_gib", "initial"):
    if not records["A"][key] == records["B"][key] == records["AB"][key]:
        raise ValueError("The three local receipts are not matched on " + key)
programs["P"] = (bundle / "reference" / "reference" / "official_initial_program.py").read_text(encoding="utf-8")
measurements = {"P": records["A"]["initial"]}
measurements.update((name, record["candidate"]) for name, record in records.items())
fixture = {
    "scope": "local_diagnostic_one_cell_not_formal",
    "case": records["A"]["case"], "seed": records["A"]["seed"], "image": records["A"]["image"],
    "programs": programs, "measurements": measurements,
    "provenance": {name: {"candidate_sha256": record["candidate_sha256"],
                          "candidate_result": record["candidate_result"].rsplit("/", 3)[-3]}
                   for name, record in records.items()},
}
target = Path(__file__).resolve().parent / "fixtures" / "local_factorial.json"
target.write_text(json.dumps(fixture, indent=1) + "\n", encoding="utf-8")
print(target, {name: round(row["common_reference_score"], 2) for name, row in measurements.items()})
