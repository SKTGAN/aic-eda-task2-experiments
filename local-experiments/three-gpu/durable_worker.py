"""SSH entry for a development worker whose evaluation survives loss of its client."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from three_gpu import ROOT, assigned_cells, atomic, framework


def retained_worker(args, request):
    cells = assigned_cells(args.case, request)
    if request["run"] not in ("balanced-search", "feedback-search") or not re.fullmatch(r"[er]-[0-9a-f]{60}", request["request"]):
        raise ValueError("Unexpected search or request ID")
    framework(args.official)
    from local_tasks.tp_gnn_local_task_definitions import DECODER_TASK, validate_program

    program = validate_program(request["program"], DECODER_TASK)
    digest = hashlib.sha256(program.encode()).hexdigest()
    slot = "+".join(args.case) + "-gpu" + str(args.gpu)
    job = ROOT / "workers" / slot / request["run"] / request["request"]
    receipt = job / "reply.json"
    spool = ROOT / "worker-requests" / slot / request["run"] / request["request"]
    spool.mkdir(parents=True, exist_ok=True, mode=0o700)
    unit = "aic-eda-worker-" + hashlib.sha256(str(job).encode()).hexdigest()[:32]
    payload = {"run": request["run"], "request": request["request"], "program": program, "cells": cells}
    wire = spool / "request.json"
    with (spool / "dispatch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if wire.exists() and json.loads(wire.read_text()) != payload:
            raise ValueError("Request ID already belongs to another payload")
        if not wire.exists():
            atomic(wire, payload)
        if not receipt.is_file() and not job.exists() and not (spool / "accepted").exists():
            # A fixed service name enforces single dispatch even if the SSH process
            # disappears after systemd receives the request, before the marker is written.
            if not active(unit):
                command = [sys.executable, "-B", str(ROOT / "three_gpu_physical.py"), *sys.argv[1:]]
                subprocess.run(["systemd-run", "--quiet", "--unit=" + unit,
                                "--property=StandardInput=file:" + str(wire),
                                "--property=StandardOutput=null",
                                "--property=StandardError=append:" + str(spool / "worker.log"),
                                "--property=UMask=0077", *command], check=True)
            (spool / "accepted").touch()

    while not receipt.is_file():
        if not active(unit) and not receipt.is_file():
            raise RuntimeError("Worker stopped without a receipt; inspect the original job")
        time.sleep(2)
    result = json.loads(receipt.read_text())
    if result.get("formal") is not False or result.get("program_sha") != digest or result.get("assigned") != cells:
        raise ValueError("Worker receipt does not match request")
    return result


def active(unit):
    return subprocess.run(["systemctl", "is-active", "--quiet", unit]).returncode == 0


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["worker"])
    parser.add_argument("--official", required=True, type=Path)
    parser.add_argument("--case", action="append", required=True)
    parser.add_argument("--gpu", required=True, type=int)
    parser.add_argument("--workers", required=True, type=int)
    parser.add_argument("--host-slots", required=True, type=int)
    args = parser.parse_args()
    text = sys.stdin.read(40000)
    if len(text) == 40000:
        raise ValueError("Worker request exceeds size limit")
    print(json.dumps(retained_worker(args, json.loads(text))))
