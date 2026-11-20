"""Prospective candidate claims and their paired official observations."""
import ast
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys


FORMAT = (
    "In each edited function's docstring use three labeled fields on separate lines. "
    "Decision: which specific partition decision will change relative to the parent, for which groups and why? "
    "Physical check: METRIC SCOPE DIRECTION (metric score, wns or tns; scope majority, all or mean; "
    "direction up, down or nondecreasing). This is a prediction on the complete official matrix paired "
    "with the actual parent. WNS/TNS compare final negative slack (closer to zero is up). "
    "Falsifier: what measured final assignment and timing evidence would contradict the mechanism? "
    "Cite observed evidence from this run when available. Treat a missing measurement as unknown."
)
LABELS = re.compile(r"^\s*(Decision|Physical check|Falsifier):[ \t]*", re.M | re.I)
METRICS = {"score": "score_delta", "wns": "wns_slack_delta_ns", "tns": "tns_slack_delta_ns"}
TEST = re.compile(r"(score|wns|tns)\s+(majority|all|mean)\s+(up|down|nondecreasing)", re.I)


def forecasts(source, components, required=False):
    """Existing shelves/receipts can predate the forecast format."""
    claims = {}
    for name, fn in zip(("loss", "decoder"), ast.parse(source).body):
        if name not in components:
            continue
        doc = ast.get_docstring(fn) or ""
        markers = list(LABELS.finditer(doc))
        fields = {m[1].lower(): doc[m.end():markers[i+1].start() if i+1 < len(markers) else len(doc)].strip()
                  for i, m in enumerate(markers)}
        test = TEST.fullmatch(fields.get("physical check", "").rstrip(".").strip())
        if len(markers) != 3 or not fields.get("decision") or not fields.get("falsifier") or not test:
            if required:
                raise ValueError("Incomplete pre-evaluation forecast in the edited " + name + " function. " + FORMAT)
            continue
        claims[name] = {"decision": fields["decision"], "physical_check": test.group().lower().split(),
                        "falsifier": fields["falsifier"]}
    return claims


def verify(summary):
    """Only the declared numerical endpoint is machine-checked; mechanism attribution remains open."""
    comparison = summary.get("parent_comparison") or {}
    attempt = summary.get("attempt") or {}
    claims = attempt.get("partition_forecasts") or {}
    rows = comparison.get("cells") or []
    valid = (summary.get("status") == "succeeded" and comparison.get("complete")
             and not comparison.get("candidate_invalid_cells")
             and len(summary.get("cells", [])) == len(rows)
             and all(c.get("valid") is True and c.get("status") == "succeeded" for c in summary["cells"])
             and len(rows) == comparison.get("expected_cells") and rows)
    observed = {}
    for cell in summary.get("cells", []):
        evidence = cell.get("partition_change_vs_initial") or cell.get("metrics") or {}
        frac = evidence.get("partition_assignment_changed_fraction")
        if cell.get("valid") and isinstance(frac, (int, float)) and 0 <= frac <= 1:
            case = observed.setdefault(cell["case"], {})
            case[str(cell["seed"])] = {"changed_fraction": frac, "after_best_global_flip": min(frac, 1-frac)}
    report = {"parent_id": attempt.get("parent_id"), "parent_source": comparison.get("parent_source"),
              "official_score_delta": comparison.get("official_score_delta"), "endpoints": {},
              "assignment_observed_vs_initial": observed,
              "assignment_reference": "official initial; not necessarily the selected parent"}
    for component, claim in claims.items():
        metric, scope, direction = claim["physical_check"]
        values = [row.get(METRICS[metric]) for row in rows]
        result = {"test": claim["physical_check"], "status": "unavailable",
                  "decision": claim["decision"][:350], "falsifier": claim["falsifier"][:350]}
        if valid and all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            def matches(v):
                return v > 0 if direction == "up" else v < 0 if direction == "down" else v >= 0
            hits = sum(matches(v) for v in values)
            avg = sum(values) / len(values)
            passed = {"mean": matches(avg), "majority": hits * 2 > len(values), "all": hits == len(values)}[scope]
            result.update(status="met" if passed else "missed", matching_cells=hits, paired_cells=len(values),
                          mean_delta=avg)
        report["endpoints"][component] = result
    return report


def local_check(source, parent, files):
    """One bounded, unscored synthetic parent/child experiment through the existing contest loader."""
    if not parent:
        return {"status": "unavailable", "issue": "parent source unavailable"}
    roots = (Path(files["framework"]).parent / "Place-3D", Path("/opt/contest/source/Place-3D"))
    place = next((p for p in roots if (p / "src/partition/lol/methods/tp_gnn.py").is_file()), None)
    python = os.environ.get("AICOMP_PROBE_PYTHON") or sys.executable
    if place is None or (python == sys.executable and
                         not all(importlib.util.find_spec(lib) for lib in ("numpy", "torch"))):
        return {"status": "unavailable", "issue": "synthetic diagnostic requires CPU torch, NumPy and Place-3D"}
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    try:
        run = subprocess.run([python, "-B", str(Path(__file__).with_name("synthetic_worker.py")), "contract"],
                             input=json.dumps({"place": str(place), "control": parent, "candidate": source}),
                             text=True, encoding="utf-8", env=env, capture_output=True, timeout=30, check=True)
        return json.loads(run.stdout)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        return {"status": "inconclusive", "issue": type(error).__name__}
