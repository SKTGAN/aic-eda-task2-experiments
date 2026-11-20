"""Select on four public development cells, then evaluate the frozen winner on two reserved cells."""
import argparse
import fcntl
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from statistics import mean


HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "score-challenge-20261118"
PROJECT = HERE.parents[1]
sys.path.insert(0, str(TOOLS))
from measure_development_panel import read, require, source_digest

PARENT = "coarse_majority"
CHALLENGERS = ("coarse_no_flip", "coarse_with_star", "coarse_star_no_flip")
DEVELOP = [f"{case}/{seed}" for seed in ("1002", "1001") for case in ("swerv_wrapper-ng45", "bp_fe-asap7")]
RESERVED = ["swerv_wrapper-ng45/1003", "bp_fe-asap7/1003"]
PARENT_REPORT = PROJECT / "exports/2026-11-19-coarse-majority-validation/public-validation.json"
PARENT_TRAIN = PROJECT / "exports/2026-11-18-local-score-challenge/coarse_majority-train.json"


def store(path, value):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def freeze(path, value):
    if path.exists():
        require(read(path) == value, f"Frozen record differs: {path}")
    else:
        store(path, value)


def verified_parent(official):
    previous = read(PARENT_REPORT)
    work = Path(previous["native_result"]).parents[2]
    require(work.parent == official / "contest-work/local-trials", "Parent native run is outside this installation")
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run([sys.executable, "-B", str(TOOLS / "export_public_validation.py"), "--work", str(work),
                        "--official", str(official), "--training-card", str(PARENT_TRAIN), "--output", folder], check=True)
        verified = read(Path(folder) / "public-validation.json")
    require(verified == previous and verified["complete"], "Parent native re-audit differs from the original archive")
    return verified


def key(row):
    return row["case"] + "/" + row["seed"]


def score(rows, cells):
    return mean(rows[cell]["score"] for cell in cells) if all(cell in rows for cell in cells) else None


def card_path(output, name, digest, cells):
    panel = source_digest("\n".join(sorted(cells)))[:12]
    return output / "panels" / f"{name}-{digest[:12]}-{panel}.json"


def load_panel(card, cells, sha, parent):
    value = read(card)
    require(value["complete"] and set(value["requested"]) == set(cells)
            and value["candidate_sha256"] == sha and value["image"] == parent["image"]
            and value["published_matrix_sha256"] == parent["matrix_sha256"],
            f"Panel identity or completion differs: {card}")
    rows = {key(row): row for row in value["cells"]}
    require(len(value["cells"]) == len(cells) and set(rows) == set(cells)
            and all(r["status"] in ("succeeded", "penalized") for r in rows.values())
            and math.isclose(score(rows, cells), value["panel_score"], abs_tol=1e-10), f"Invalid panel: {card}")
    return rows


def transient(detail):
    text = detail.lower()
    return any(token in text for token in (
        "insufficient available memory", "another native physical job occupies", "cannot connect to the docker daemon",
        "error during connect", "connection reset by peer", "context deadline exceeded", "lease expired",
        "lease has expired", "temporary failure", "out of memory", "temporarily unavailable",
        "connection refused", "transport is closing", "unexpected eof", "oomkilled"))


def retry_evidence(card, log, official):
    detail = log.read_text(encoding="utf-8", errors="replace")[-8192:]
    if card.exists():
        failure = read(card).get("failure", {})
        detail += "\n" + failure.get("message", "")
        if failure.get("log"):
            native_log = Path(failure["log"]).read_text(encoding="utf-8", errors="replace")
            detail += "\n" + native_log[-8192:]
            for line in native_log.splitlines():
                if line.startswith("Artifacts: ") and failure.get("cell"):
                    work = Path(line.removeprefix("Artifacts: ")).resolve()
                    if work.parent == official / "contest-work/local-trials":
                        receipt = work / "evaluation/cells" / failure["cell"] / "cell.json"
                        if receipt.is_file():
                            detail += "\n" + str(read(receipt).get("error_message", ""))
    return detail


def measure(official, out, name, sha, cells, parent, progress):
    card = card_path(out, name, sha, cells)
    cmd = [sys.executable, "-B", "-u", str(TOOLS / "measure_development_panel.py"), "--official", str(official),
           "--candidate", str(out / "sources" / (name + ".py")), "--output", str(card.parent), "--cells", *cells]
    for attempt in range(1, 5):
        log = out / f"{name}-{cells[0].split('/')[1]}-{time.time_ns()}.log"
        progress.update(active_candidate=name, active_panel=str(card), attempt=attempt, log=str(log))
        store(out / "summary.json", progress)
        print(f"Checking or running {name} on {len(cells)} cells, log {log.name}", flush=True)
        with log.open("x", encoding="utf-8") as stream:
            status = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT).returncode
        if status == 0:
            return load_panel(card, cells, sha, parent)
        detail = retry_evidence(card, log, official)
        if attempt == 4 or not (status in (-9, -15) or transient(detail)):
            raise RuntimeError(f"{name} panel stopped with exit {status}, see {log}: {detail[-1200:]}")
        print(f"Transient worker failure, retrying verified work in {30 * attempt}s", flush=True)
        time.sleep(30 * attempt)


def summarize(rows, parent_rows):
    result = {"cells": [rows[k] for k in DEVELOP + RESERVED if k in rows]}
    for field, cells in (("development_four", DEVELOP), ("reserved_two", RESERVED), ("public_six", DEVELOP + RESERVED)):
        value = score(rows, cells)
        result[field] = value
        result[field + "_delta_from_parent"] = None if value is None else value - score(parent_rows, cells)
    return result


def run(official, out):
    parent = verified_parent(official)
    parent_rows = {key(row): row for row in parent["cells"]}
    names = (PARENT, *CHALLENGERS)
    sources = out / "sources"
    sources.mkdir(exist_ok=True)
    hashes = {}
    for name in names:
        copy = sources / (name + ".py")
        if not copy.exists():
            original = (TOOLS if name == PARENT else HERE) / copy.name
            tmp = copy.with_suffix(".py.tmp")
            tmp.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")
            tmp.replace(copy)
        hashes[name] = source_digest(copy.read_text(encoding="utf-8"))
    require(hashes[PARENT] == parent["candidate_sha256"], "Frozen parent source differs from its native result")
    plan = {"type": "local public validation development", "official_root": str(official), "baseline": "loss_decoder",
            "image": parent["image"], "public_matrix_sha256": parent["matrix_sha256"], "source_sha256": hashes,
            "parent_native_result_sha256": parent["native_result_sha256"], "development": DEVELOP, "reserved": RESERVED,
            "selection": "highest four-cell mean of official clipped scores, including physical penalties",
            "tie_preference": list(names)}
    freeze(out / "plan.json", plan)
    plan_sha = hashlib.sha256((out / "plan.json").read_bytes()).hexdigest()
    standings = {name: {"status": "awaiting_development", **summarize({}, parent_rows)} for name in names}
    standings[PARENT] = {"status": "previous_native_six_verified", **summarize(parent_rows, parent_rows),
                         "training_nine": parent["training_score"]}
    progress = {"status": "development", "plan_sha256": plan_sha, "candidates": standings,
                "selection_file": str(out / "selection.json")}
    store(out / "summary.json", progress)
    panels = {PARENT: {k: parent_rows[k] for k in DEVELOP}}
    selection_path = out / "selection.json"
    try:
        for name in CHALLENGERS:
            if selection_path.exists():
                card = card_path(out, name, hashes[name], DEVELOP)
                panels[name] = load_panel(card, DEVELOP, hashes[name], parent)
            else:
                panels[name] = measure(official, out, name, hashes[name], DEVELOP, parent, progress)
            standings[name] = {"status": "development_complete", **summarize(panels[name], parent_rows)}
            store(out / "summary.json", progress)
        scores = {n: score(panels[n], DEVELOP) for n in names}
        winner = max(names, key=scores.__getitem__)
        selection = {"plan_sha256": plan_sha, "candidate": winner, "candidate_sha256": hashes[winner],
                     "development_cells": DEVELOP, "development_scores": scores}
        freeze(selection_path, selection)
        progress.update(status="winner_frozen", winner=winner)
        store(out / "summary.json", progress)
        if winner != PARENT:
            reserved = measure(official, out, winner, hashes[winner], RESERVED, parent, progress)
            standings[winner] = {"status": "winner_confirmed", **summarize({**panels[winner], **reserved}, parent_rows)}
        else:
            standings[PARENT]["status"] = "winner_confirmed_from_previous_native_six"
        for n in CHALLENGERS:
            if n != winner:
                standings[n]["status"] = "not_selected"
        progress.update(status="complete", active_candidate=None, active_panel=None)
        print(f"Winner {winner}, four-cell score {scores[winner]:.6f}, six-cell score {standings[winner]['public_six']:.6f}", flush=True)
    except Exception as error:
        progress.update(status="stopped", error=str(error))
        raise
    finally:
        store(out / "summary.json", progress)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    official = args.official.resolve(strict=True)
    out = args.output.resolve()
    require(out != official and official not in out.parents, "Export outside the official installation")
    out.mkdir(parents=True, exist_ok=True)
    with (out / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        run(official, out)


if __name__ == "__main__":
    main()
