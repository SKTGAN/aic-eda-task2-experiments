"""Build the development agent from verified historical receipts, outside the submission tree."""

import ast
import hashlib
import json
import statistics
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
RUN = PROJECT / "exports/2026-11-19-claude-expert-audit/runs/15332-claude-v3"
BASE = PROJECT / "harness-parent-followup/next-harness/AgenticBench/agent/loss_decoder"


def load(path):
    return json.loads(path.read_bytes())


def build():
    from memory import measured_row
    history = []
    sources = {}
    for n in range(1, 11):
        folder = RUN / ("round-%02d" % n)
        receipt, gen = load(folder / "receipt.json"), load(folder / "generation.json")
        o, matrix = receipt["overview"], receipt["official_receipt"]["matrix"]
        assert o["round"] == n and o["status"] == receipt["ledger"]["status"] == "succeeded"
        assert o["candidate_id"] == receipt["ledger"]["candidate_id"]
        assert matrix["complete"] and matrix["all_valid"] and len(matrix["cells"]) == 9
        assert abs(statistics.mean(c["score"] for c in matrix["cells"]) - o["score"]) < 1e-7
        source = (folder / "candidate.py").read_bytes()
        assert hashlib.sha256(source).hexdigest() == gen["verified_source_sha256"]
        funcs = ast.parse(source).body
        changed = list(gen["candidate_explanation"])
        mechanism = {k: (ast.get_docstring(funcs[{"loss": 0, "decoder": 1}[k]]) or gen["candidate_explanation"][k]) for k in changed}
        row = measured_row(n, "15332", o["candidate_id"], o["parent_id"], o["score"],
                           matrix["cells"], mechanism, o["status"])
        row["source_sha256"] = gen["verified_source_sha256"]
        row["request_id"] = o["request_id"]
        history.append(row)
        sources[o["candidate_id"]] = source
    assert len(sources) == 10 and len({tuple(sorted(r["cells"])) for r in history}) == 1
    archive = {"run": "15332-claude-v3", "development_only": True, "rounds": history}
    (HERE / "ten-round-memory.json").write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(HERE / "dev-harness.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for name in ("agent.py", "memory.py", "ten-round-memory.json"):
            zipf.write(HERE / name, name)
        for name in ("agent.py", "candidate_reply.py", "paired_feedback.py"):
            zipf.write(BASE / name, "parent_harness.py" if name == "agent.py" else name)
        zipf.write(BASE / "prompt.md", "editor.md")
        zipf.write(PROJECT / "official/contest-source/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py","program.py")
        for cid, source in sources.items():
            zipf.writestr("observed/" + cid + ".py", source)
    return archive


if __name__ == "__main__":
    build()
