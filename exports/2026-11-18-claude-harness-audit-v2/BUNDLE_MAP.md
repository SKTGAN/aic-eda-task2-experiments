# Audit bundle map

Start with `START_HERE.md`. `CLAUDE_PROMPT.txt` can be copied into the chat
alongside this ZIP. `ROLLING_PROTOCOL.md` is the proposed decision process
and `RESEARCH_NOTES.md` connects the proposal to the original sources.

| Location | Material |
|---|---|
| `sources/branching/` | Branch selection, decision evidence, optional feedback, and existing development tests |
| `sources/two-stage/` | Existing two-stage planning and generation source |
| `sources/claude-r3/` | Claude review candidate and replay/compatibility code |
| `evidence/runs/` | Historical training and public-reference comparison, selected prompts and receipts, and a branching replay |
| `evidence/local-factorial/` | Same-cell exact A/B/AB programs, matched baseline receipts and source-hash verification |
| `evidence/rolling-audit/` | Read-only prototype that reuses exact measured removal controls, flags a missing counterfactual, and computes the weak-target/protection deltas on one real nine-cell comparison |
| `reference/` | Task brief, algorithm interface, and evaluation context |

After extracting the ZIP, run `python -B evidence/rolling-audit/rolling_example.py`
from the bundle root. It uses the attached archived files and the standard
library. It runs no candidate code, model call, or scored physical evaluation.
The example merely illustrates how evidence selection and paired checks could
be integrated. `evidence/rolling-audit/example-output.json` is its output
from the verification run. A counterfactual missing-receipt example excludes
one measured control to demonstrate how uncertainty is represented.

The bundled source is available for review. Historic code, scores, and public
validation artifacts are development evidence, outside a future formal
run's prompt. `SOURCE_PROVENANCE.json` records changes made to translate some
source comments and prompts into English for review.
