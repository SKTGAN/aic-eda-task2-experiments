"""Run at most one optional background CPU experiment beside the blocking contest evaluation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from uuid import uuid4


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class CPUChecks:
    def __init__(self, files):
        self.directory = Path(files["workspaces"]) / "cpu_checks_v1"
        framework = Path(files["framework"])
        roots = (framework.parent / "Place-3D", Path("/opt/contest/source/Place-3D"))
        self.place = next((p for p in roots if (p / "src/partition/lol/methods/tp_gnn.py").is_file()), None)
        self.python = os.environ.get("AICOMP_PROBE_PYTHON") or sys.executable
        deps = (Path(self.python).is_file() if self.python != sys.executable else
                all(importlib.util.find_spec(lib) for lib in ("numpy", "torch")))
        self.available = bool(self.place and deps)
        self.thread = None
        self.active = None

    def path(self, request_id, mode):
        if not re.fullmatch(r"[er]-[0-9a-f]{12,64}", request_id):
            return None
        return self.directory / (request_id + "-" + mode + ".json")

    def read(self, request_id, mode):
        path = self.path(request_id, mode)
        if path is not None:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
        if mode == "ablation" and request_id == self.active and self.thread and self.thread.is_alive():
            return {"status": "pending"}
        return {"status": "unavailable"}

    def run_check(self, mode, request_id, control_id, control, candidate):
        identity = {"control": control_id, "control_sha256": digest(control), "source_sha256": digest(candidate)}
        path = self.path(request_id, mode)
        cached = self.read(request_id, mode)
        if all(cached.get(k) == v for k, v in identity.items()) and cached.get("status") in ("ok", "invalid"):
            return cached
        if self.available:
            env = dict(os.environ, CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       OPENBLAS_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
            try:
                run = subprocess.run([self.python, "-B", str(Path(__file__).with_name("synthetic_worker.py")), mode],
                                     input=json.dumps({"place": str(self.place.resolve()), "control": control,
                                                       "candidate": candidate}), capture_output=True, text=True,
                                     encoding="utf-8", env=env, timeout=25 if mode == "contract" else 45, check=True)
                result = json.loads(run.stdout)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                result = {"status": "inconclusive", "issue": type(error).__name__}
        else:
            result = {"status": "inconclusive", "issue": "CPU torch/numpy or published Place-3D runtime unavailable"}
        result.update(identity)
        if path is not None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix("." + uuid4().hex + ".tmp")
                tmp.write_text(json.dumps(result, allow_nan=False), encoding="utf-8")
                tmp.replace(path)
            except OSError:
                result["storage"] = "unavailable"
        return result

    def start(self, request_id, control_id, control, candidate):
        if self.thread and self.thread.is_alive():
            return "busy"
        if not self.available:
            return "unavailable"
        self.active = request_id
        self.thread = threading.Thread(target=self.run_check, args=("ablation", request_id, control_id, control, candidate),
                                       daemon=True)
        self.thread.start()
        return "started"

    def evidence(self, rows, history=()):
        result = []
        for row in rows:
            if not row or any(item["id"] == row["candidate_id"] for item in result):
                continue
            attempt = row.get("attempt") or {}
            request_id = attempt.get("retry_of") or row["request_id"]
            result.append({"id": row["candidate_id"], "contract": self.read(request_id, "contract"),
                           "ablation": self.read(request_id, "ablation")})
        detailed = {item["id"] for item in result}
        for row in history:
            if row["candidate_id"] in detailed:
                continue
            request_id = (row.get("attempt") or {}).get("retry_of") or row["request_id"]
            report = self.read(request_id, "ablation")
            result.append({"id": row["candidate_id"], "status": report["status"], "control": report.get("control"),
                           "candidate_rows": [arm for arm in report.get("rows", []) if arm["arm"] == "candidate"]})
        return result

    def finish(self):
        if self.thread:
            self.thread.join(48)

