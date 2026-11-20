"""Offline release check using Claude's archived bridge and five real receipts; creates no new scores."""
import ast
from pathlib import Path
import re
import sys
import tempfile
import types
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "AgenticBench/agent/loss_decoder"
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT / "official/contest-source/AgenticBench"))
# Import the shipped validator without importing the unrelated physical-flow runner at package initialization.
for package in ("local_bench", "local_tasks"):
    module = types.ModuleType(package)
    module.__path__ = [str(PROJECT / "official/contest-source/AgenticBench" / package)]
    sys.modules[package] = module
from local_tasks.tp_gnn_local_task_definitions import validate_program, DECODER_TASK


def fixture_source(record):
    # Adapt only the edited function's documentation to the new protocol.
    source = record["source"]
    fn = ast.parse(source).body[int(record["intent"] == "decoder_only")]
    lines = source.splitlines(keepends=True)
    doc = fn.body[0]
    assert ast.get_docstring(fn)
    lines[doc.lineno - 1:doc.end_lineno] = [
        '    """Fixture hypothesis.\n'
        '    Decision: Groups near the parent area cutoff change their relative order.\n'
        '    Physical check: tns majority up\n'
        '    Falsifier: Stable final groups with worsening paired TNS contradict this prediction.\n'
        '    """\n']
    augmented = "".join(lines)
    validate_program(augmented, DECODER_TASK)
    record["source"] = augmented
    return record


def main():
    archive = PROJECT / "exports/claude-supervisor-audit.zip"
    for path in AGENT.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=8)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        with ZipFile(archive) as z:
            prefix = "task2-supervisor-audit/"
            for name in z.namelist():
                if name.startswith((prefix + "replay/", prefix + "tests/")):
                    z.extract(name, work)
            assert (AGENT / "program.py").read_bytes() == z.read(prefix + "K1S/AgenticBench/agent/loss_decoder/program.py")
        work = work / prefix
        sys.path.insert(0, str(work / "replay"))
        import replay
        expert = (AGENT / "prompt.md").read_text(encoding="utf-8").split("## Offline Expert Knowledge")[1]
        units = 6 + len(re.findall(r"[\u3400-\u9fff]|[0-9]+", expert)) + 2*len(re.findall(r"[A-Za-z]+", expert))
        assert units <= 200
        print("expert units incl. heading:", units)
        for variant in ("X", "Y"):
            path = work / "replay/windows" / variant
            rounds = [fixture_source(r) for r in replay.load_window(path)]
            # Alternative proposals in this test echo A, independent of the two recorded submissions.
            for r in rounds:
                r["alternatives"] = []
            extra = ([fixture_source(replay.load_round(work / "replay/after-window/X/round-03"))]
                     if variant == "X" else [])
            wd = work / variant
            wd.mkdir()
            agent, folder = replay.support.load_agent(AGENT, wd)
            (folder / "opening.txt").write_text(rounds[0]["intent"] + "\n", encoding="utf-8")
            initial = replay.official_parent_program(path)
            bridge = replay.ReplayBridge(wd, rounds, initial, followups=extra)
            try:
                agent.Agent().run(bridge)
            except replay.Stop:
                pass
            events = replay.events(folder)
            recent = [(e["event"], e.get("reason")) for e in events[-7:]]
            assert len(bridge.order) == 2 + len(extra), recent
            assert sum("## Offline Expert Knowledge" in r["system"] for r in bridge.requests) == 1
            checkpoints = [e["checkpoint"] for e in events if e["event"] == "supervisor_review"]
            assert checkpoints == list(range(2, 3 + len(extra))), checkpoints
            for i, request in enumerate(bridge.later, 2):
                req = request["request"]
                assert req["parent_program"] and req["supervisor_review"]["checkpoint"] == i
                checks = req["prior_forecast_checks"]
                assert len(checks) == i
                for c in checks:
                    endpoint, = c["endpoints"].values()
                    assert endpoint["status"] in ("met", "missed") and endpoint["paired_cells"] == 9, endpoint
                    assert endpoint["decision"] and endpoint["falsifier"]
            receipts = [e for e in events if e["event"] == "evaluated"]
            assert all(e["forecast_check"]["endpoints"] for e in receipts)
            assert len(bridge.later) == 1 + len(extra)
            from partition_review import verify, forecasts
            assert not forecasts(initial, ["loss"])
            try:
                forecasts(initial, ["loss"], required=True)
            except ValueError:
                pass
            else:
                raise AssertionError("missing forecast accepted")
            incomplete = dict(receipts[0], cells=receipts[0]["cells"][:-1])
            assert all(e["status"] == "unavailable" for e in verify(incomplete)["endpoints"].values())
            assert len(agent.load_attempts(folder / "search.jsonl")) == len(bridge.order)
            print(variant, "archived receipts", len(receipts), "checkpoints", checkpoints,
                  "next prompts", len(bridge.later))


if __name__ == "__main__":
    main()
