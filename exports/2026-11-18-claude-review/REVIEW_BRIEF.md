# Task 2 Harness review request

Please use the attached run evidence to propose specific changes to the
Harness for the 3D chip netlist partitioning task. The Harness steers the
contest model, DeepSeek, through candidate generation, validation, and
selection. Claude authored two Harness versions represented here.

| Folder | Run and server | Evidence | Outcome |
|---|---|---|---|
| `claude-original/` | Claude original revision, 15332 | 10 submitted programs, 90 training cells, 6 public validation cells | Best training **34.75** in round 4, tied by round 6. Round 4 was selected. Public validation **-4.35**. |
| `claude-new/` | Claude newer Harness, 27528 | 3 submitted programs, 9 physical cells, complete available diagnostic model trace | Best **30.98** on a reduced panel of three designs using seed 1002. |
| `ours-new/` | Our evidence-driven Harness, 10820 | 4 submitted programs, 36 physical cells, 11 saved requests and replies | Best full training **26.49** in round 3. Round 4 scored **25.01**. The Harness crashed while processing that result. |
| `ours-previous/` | Previous comparison Harness from the supplied two-server archive, 27528 | 5 submitted programs, 4 complete matrices, 3 physical receipts from interrupted round 5 | Best full training **18.22** in round 2. |

The published starting reference for the full training matrix is **20.4251**.
It is a published reference rather than a repeated same-host measurement for
every run. Compare candidate and baseline on the same design and seed when the
evidence allows. Keep the three-cell panel, nine-cell training scores, six-cell
public validation, and local single-cell diagnostics distinct.

In public validation, the selected original Claude candidate averaged
**+10.34** on `swerv_wrapper-ng45` and **-19.03** on `bp_fe-asap7`. The six
cell scores and raw timing receipts are in `claude-original/public-validation.json`
and `claude-original/raw/validate/`.

## Where to look

1. Start with each run's `RUN_SUMMARY.md` and the top-level `run-index.json`.
2. Read `rounds/round-NN.json` for the submitted change, its parent and decision,
   the saved feedback, and physical cell results. `programs/` contains every
   submitted candidate, including the interrupted one. `training-cells.csv`
   gives WNS, TNS, cut nets, assignment movement when available, and the
   front-end and back-end timings and exits.
3. `interactions/all-rounds.jsonl` holds each recorded event in order.
   `interactions/round-NN.jsonl` groups the logged generation and assessment
   around each submitted candidate. The raw diagnostic model transcript and
   bridge feedback are also present for the reduced-panel run.
4. The original Claude Harness did not record exact model request or reply
   bodies. Its static templates, accepted program source, opening reviews,
   rejection reasons, evaluation feedback events, API usage, controller
   receipts, and physical logs are available. The supplied evidence does not
   reconstruct missing messages. In the evidence-driven run, round 4 has a
   complete evaluator receipt and a crash witness, but no round-4 Harness
   feedback event.
5. Each folder contains a standalone `harness-package-en.zip` with the captured
   agent source and English prompts. The provenance manifest identifies files
   translated for review. `raw/` contains original receipt structure, detailed
   numeric fields and log excerpts, with translation and redaction as noted.
   Long physical logs are bounded and labeled. Large placement and netlist
   artifacts are outside the scope of this review.
6. `context/previous-review/` preserves the task reference and the older
   comparison notes from the supplied two-server archive. The newer run
   folders supersede the partial progress counts in those historical notes.
   `context/local-followup/` contains controlled local experiments.

## Questions to answer

- Identify where the loop loses information between the evaluator receipt and
  the next proposal. Quote the evidence by run, round, and cell. Identify which
  claims are impossible to check from the original log and specify the fields
  you would record on the next run.
- Explain why the 34.75 training candidate did not transfer to public
  validation. Distinguish supported findings from hypotheses, and use the
  validation only for retrospective analysis. Propose a training-only
  candidate selection rule with a test for gains concentrated on one case or
  seed.
- Compare useful mechanisms by observed effect on die assignment and final
  WNS/TNS. Separate inert edits, full die flips, local boundary changes, and
  runtime or environment failures. Where the same visible score recurs, check
  source identity, partition evidence, and timing per cell before interpreting it.
- Propose a concrete Harness revision. Show what the model would receive, how
  the next experiment would be chosen, how to decide which candidates to
  retain, and how to spend the ten-candidate budget. Prioritize changes to
  feedback quality and experimental coverage over prompt length.
- Include a cheap candidate gate and a replay check that would catch the
  Python 3.8 bit-count crash before a costly evaluation. Keep evaluation
  accounting and scoring in the official framework.
- Provide an ordered implementation plan with likely code locations and one
  budget-matched verification plan. Keep development diagnostics separate from
  the final Harness; official runs start from the published baseline and use
  only the permitted information and official budget interface.
