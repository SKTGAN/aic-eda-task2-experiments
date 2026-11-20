"""One development-only physical cell using the unchanged official initial program and reference."""
from pathlib import Path
import json
import sys
base = Path("/root/rolling-3090")
src = base / "official/contest-source"
framework = src / "AgenticBench"
data = base / "official/contest-data/task2"
work = base / "baseline-diagnostic"
sys.path.insert(0, str(framework))
from contest2.runner import _runtime
from local_bench.matrix import LocalEvaluationMatrix
from local_bench.model import load_task, load_candidate
from local_bench.program_bridge import initial_program_text, materialize_program
from local_bench.verifier import verify_candidate
from grt_bench.common import write

work.mkdir(exist_ok=True)
matrix_path = data / "loss_decoder/train/qualified_matrix.json"
definition = json.loads(matrix_path.read_text())
spec = load_task(framework / "local_tasks/tp_gnn_loss_decoder_timing")
row, = [r for r in definition["cells"] if r["case"] == "bp_fe-ng45" and r["seed"] == "1001"]
for field in ("base_config", "baseline_run", "reference_run"):
    row[field] = str((matrix_path.parent / row[field]).resolve(strict=True))
definition.update(cases=[row["case"]], cells=[row], seeds=[s for s in definition["seeds"] if s["id"] == row["seed"]])
write(work / "one-cell.json", definition)
matrix = LocalEvaluationMatrix(work / "one-cell.json", spec)
candidate = materialize_program(spec, initial_program_text(spec,load_candidate(spec.initial_candidate)), src)
verify_candidate(spec, candidate, src)
write(work / "initial/candidate.json", candidate)
transport, _ = _runtime(data / "runtime.json", work_root=work, private_queue=True)
result = matrix.evaluate(work / "initial", src, work / "physical", transport=transport, compact=True)
cell = json.loads((work / "physical/cells/bp_fe-ng45/1001/cell.json").read_text())
print(json.dumps({k:cell.get(k) for k in ("case","seed","status","valid","score","error_message")}), flush=True)
if not cell.get("valid") or cell.get("status") != "succeeded":
    raise RuntimeError("Official initial program failed the physical diagnostic")
