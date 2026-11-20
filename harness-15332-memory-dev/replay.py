"""Exercise the packaged agent with the real ten-round memory and two mocked new receipts."""

import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "harness-parent-followup/tests"))
import stubs
from test_loop import Proposer, gain


def replay():
    stubs.install()
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "package"
        with zipfile.ZipFile(HERE / "dev-harness.zip") as z:
            z.extractall(folder)
        for q in folder.rglob("*.py"):
            ast.parse(q.read_bytes(), feature_version=(3, 8))
        sys.path.insert(0, str(folder))
        module = importlib.import_module("agent")
        history, sources = module.observed()
        for ix, row in enumerate(history, 1):
            assert len(row["cells"]) == 9 and row["round"] == ix and ix in sources
        proposer = Proposer()
        calls = []

        def model(bridge, system, request):
            n = len(request["memory"]["rounds"])
            assert n == 10 + len(bridge.order)
            stage = "editor" if "parent_program" in request else "planner"
            calls.append((stage, n))
            if stage == "editor":
                assert request["parent_program"] == (sources[4] if n == 10 else bridge.records[bridge.order[0]]["source"])
                return proposer(bridge, system, request)
            return stubs.completed(json.dumps({"parent_round":4 if n == 10 else 11,
                "component":"loss","evidence":[{"round":4,"cell":"ariane133-ng45/1002"},
                {"round":7 if n == 10 else 11,"cell":"ariane133-ng45/1002"}],"experiment":"replay"}))

        ctx=stubs.Bridge(tmp,model,gain(),evaluation_limit=2)
        selected=module.Agent().run(ctx)
        assert calls == [("planner",10),("editor",10),("planner",11),("editor",11)]
        assert module.Agent().run(ctx)==selected and len(ctx.order)==2 and len(calls)==4
        print("memory coverage 10 rounds, 90 cells; both model turns saw 10 then 11 rounds;")
        print("parent source verified; completed restart issued zero new requests or evaluations.")


if __name__ == "__main__":
    replay()
