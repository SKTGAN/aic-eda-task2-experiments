# Bundle map

| Location | Use |
|---|---|
| `START_HERE.md` | Audit request, current obstacles, and requested deliverables |
| `EXPERIMENT_PROTOCOL.md` | Proposals for synthetic self-tests, an attribution table, selective ablation, and budget-matched Harness evaluation |
| `RESEARCH_NOTES.md` | Primary literature and what can be adapted |
| `sources/branching/` | Current branching candidate for review, including its decision rules, paired feedback and existing development tests |
| `sources/two-stage/` | Fourth machine's available two-stage planner and generator source for comparison |
| `sources/claude-r3/` | Additional Claude revision and replay / compatibility tests. Its inclusion establishes source availability rather than a new measured score. |
| `evidence/local-factorial/` | Three matched candidate sources and paired local receipts. The shared start comes from the same baseline record for all three. |
| `evidence/runs/` | Selected formal and diagnostic training inputs, per-cell tables, lineage, replay, and public-reference comparison |
| `reference/` | Organizer task brief and agent/algorithm interfaces already used by the earlier audit |
| `SOURCE_PROVENANCE.json` | Before-and-after hashes for copies whose natural-language text was translated |

In the branching source, read `search_control.py` for parent selection,
`decision_evidence.py` for historical comparison and timing duplicates,
`paired_feedback.py` for cell-level attribution, and `agent.py` for model
dispatch and result persistence. In the two-stage source, read `ask_model()`
and the `plan_cache` / `generation` code in `agent.py`.

From the extracted bundle root, run:

```text
python evidence/local-factorial/check_factorial.py
```

This read-only check verifies shared baseline, exact candidate source hashes,
and that AB uses A's loss and B's decoder as measured. It prints the local
interaction contrast and the raw timing measurements without running EDA or
calling a model. Its use is retrospective development audit. Existing Harness
tests that import the official framework need the organizer task package.

The audit contains selected traces for efficient reading. The earlier
three-server evidence archive remains the source for the complete 22 candidate
programs and detailed physical logs. English prompt copies retain their
interface; hashes identify translation differences. This archive is for
review. Official entries use the organizer runtime and task instructions.
