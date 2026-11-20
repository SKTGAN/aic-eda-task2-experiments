"""Review the fourth server's development runs from the host, outside the Agent."""
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean

ROOT = Path("/root/aic-eda-fourth")
ARM = ROOT / "arm"
TARGET = 34.75499580780448
TREND_FLOOR = 29.427746177483954


def snapshot(work):
    db = work / "control/budget.sqlite"
    if not db.is_file():
        return []
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10) as conn:
        rows = conn.execute("SELECT request_id,status FROM evaluations WHERE status IN "
                            "('accepted','succeeded','failed') ORDER BY accepted_at,rowid").fetchall()
    results = []
    for request_id, status in rows:
        result = {"request": request_id, "status": status}
        if status == "succeeded":
            path = work / "evaluations" / request_id / "evaluation_result.json"
            metrics = json.loads(path.read_text())["metrics"]
            cells = metrics["matrix"]["cells"]
            groups = {case: [row["score"] for row in cells if row["case"] == case]
                      for case in ("ariane133-ng45", "bp-ng45", "bp_fe-ng45")}
            if not metrics["matrix"]["complete"] or any(len(group) != 3 for group in groups.values()):
                raise ValueError("Official success lacks a complete nine-cell matrix")
            result.update(score=metrics["combined_score"], cases={k: mean(v) for k, v in groups.items()},
                          penalties=sum(row["status"] == "penalized" for row in cells))
        results.append(result)
    return results


def verdict(rows):
    scored = [row for row in rows if "score" in row]
    if len(scored) >= 3 and max(row["score"] for row in scored) >= TARGET:
        return "continue_best"
    if len(rows) < 4 or any(row["status"] == "accepted" for row in rows):
        return "wait"
    if len(scored) != len(rows):
        return "review_incomplete"
    previous = max(scored[:-1], key=lambda row: row["score"])
    last = scored[-1]
    improved = sum(last["cases"][k] > v for k, v in previous["cases"].items())
    if (last["score"] >= TREND_FLOOR and last["score"] > previous["score"]
            and improved >= 2 and last["penalties"] <= previous["penalties"]):
        return "continue_trend"
    return "change"


def owned_agent(work):
    for record in work.glob("scratch/*/container-startup.json"):
        data = json.loads(record.read_text())
        if data["returncode"] != 0:
            continue
        cid = data["stdout"].strip()
        if len(cid) != 64 or any(ch not in "0123456789abcdef" for ch in cid):
            continue
        probe = subprocess.run(["docker", "inspect", cid], text=True, capture_output=True)
        if probe.returncode:
            continue
        info = json.loads(probe.stdout)[0]
        if info["State"]["Running"] and any(m["Destination"] == "/workspace/agent" and
                Path(m["Source"]).resolve() == work / "participant-agent/loss_decoder" for m in info["Mounts"]):
            return cid, info["State"]["Paused"]
    raise RuntimeError("No live Agent owned by the requested run")


def hold(work, desired):
    cid, paused = owned_agent(work)
    if paused != desired:
        subprocess.run(["docker", "pause" if desired else "unpause", cid], check=True)


def review(arm, work, unit):
    while True:
        rows = snapshot(work)
        decision = verdict(rows)
        if decision.startswith("continue"):
            hold(work, False)
        elif len(rows) >= 4:
            hold(work, True)
        if decision != "wait":
            report = {"action": decision, "work": str(work), "rounds": rows}
            (arm / "round-review.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report), flush=True)
            return decision
        if subprocess.run(["systemctl", "is-active", "--quiet", unit]).returncode:
            raise RuntimeError("Run exited before the fourth-round decision; inspect runner logs")
        time.sleep(10)


def start_comparison():
    arm = ROOT / "claude-control"
    work = arm / "run-01"
    unit = "aic-eda-fourth-claude"
    if not work.exists() and subprocess.run(["systemctl","is-active","--quiet",unit]).returncode:
        subprocess.run(["systemd-run", "--unit=" + unit,
            "--working-directory=" + str(arm / "contest-source/AgenticBench"),
            "--property=StandardOutput=append:" + str(arm / "live.log"),
            "--property=StandardError=append:" + str(arm / "live.log"),
            "/usr/bin/python3", "-Bu", "-m", "contest2", "run", "--baseline", "loss_decoder",
            "--source", str(ROOT / "official/contest-source"), "--data-root", str(ROOT / "official/contest-data/task2"),
            "--runtime", str(arm / "runtime.json"), "--work-root", str(work), "--agent-cpu", "2",
            "--agent-memory-gb", "4", "--api-key-file", "/root/.config/aic-eda/deepseek.key"], check=True)
    return review(arm, work, unit)


if __name__ == "__main__":
    if review(ARM, ARM / "run-01", "aic-eda-fourth-live") == "change":
        print("Switching to the archived Claude Harness from the official initial program", flush=True)
        print("Claude review:", start_comparison(), flush=True)
