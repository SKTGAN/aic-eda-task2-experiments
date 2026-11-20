# Audit request for Claude

Audit the Harness for an autonomous EDA contest entry. We want a concrete
patch, or an ordered implementation proposal with code locations and executable
acceptance tests, for an agent that can explain what each trial learned and use
that evidence to choose, test, and combine changes to the partitioning algorithm.
The attached source and runs are development evidence. Begin with the current
branching Harness in `sources/branching/` and compare the two-stage planner in
`sources/two-stage/`. The archived Claude R3 is an additional design reference.

The task starts from the organizer's `loss_decoder` program. Candidate edits
target `compute_tp_gnn_loss` and `decode_tp_gnn_embeddings`. One formal
candidate evaluation runs three training designs with three seeds per design.
Use the official evaluator and budget interface for all scored evaluations.
The formal budget is at most 10 candidate evaluations and RMB 15 in model
usage per run. Select the submitted result from complete official training
receipts. Run public validation after candidate selection. Treat the old runs
below and all public data here as material for developing and auditing the
Harness, outside a future live search's prompt context.

## Observed difficulties

| Observation | Evidence | Audit question |
|---|---|---|
| The search can get stuck at the baseline or circle the champion. | Our old run returned to the official start for its first four candidates. Claude's original run used round 4 as the parent for rounds 5–10. Round 6 produced identical WNS, TNS, and scores on all nine cells. | How should repetition, complementarity, and the marginal value of another trial determine the next parent? What would trigger a branch change before another expensive measurement? |
| Detailed feedback can bury the action. | In our evidence-driven round 4, the user JSON values totaled about 27,000 characters, with about 17,400 in `last_trial`. Parent feedback and decision evidence repeated key facts. | Can deterministic code select a compact paired table, the decisive cells, and up to three relevant previous experiments with explicit evidence IDs? |
| More reasoning can be spent on useful diagnostics. | The evidence-driven run requested low effort on all 11 saved calls. The 27528 diagnostic used three high-effort planning calls and three low-effort code calls. Its results were measured on three cells, a different panel from the nine-cell formal evaluations. Recorded token counts do not establish thinking duration. | When should a high-effort planner compare competing explanations? How can a code-generation call receive the exact test hypothesis and protected gains without repeating the archive? |
| Correctness failures cost turns or end the whole search. | Three first-round proposals in the evidence-driven run were rejected for unsupported code operations or names. Its fourth official matrix scored 25.01, then auxiliary feedback code crashed on `int.bit_count()` inside Python 3.8. The current branching source saves official feedback before optional analysis. | What useful tests can the Harness itself run under the actual Agent runtime, and how should failed probes guide a bounded repair before submission or trigger degraded feedback after it? |
| Repairing the worst cell can sacrifice existing gains. | From evidence-driven rounds 3→4, the target `bp_fe-ng45/1001` improved 22.99→39.41. `ariane133-ng45/1002` and `1003` fell 40.50→23.64 and 54.78→24.10. Aggregate went 26.49→25.01. | Can a plan record a target, a small set of gains to protect, and a falsifier? How should the next decision react if the target improves while the protection condition fails? |
| Individually useful edits can interfere when combined. | In the matched local `bp_fe-ng45/1001` comparison, the start scored 15.77. A fixed hard-negative margin scored 50.46, a decoder tier swap scored 52.65, and their exact combination scored 28.37. The interaction contrast was −58.96 points on this cell. | When are two changes safe to combine as code? Which comparison will tell us whether they reinforce each other physically, and when should the agent retain the best singleton? |

The original Claude round-4 candidate's nine-cell training score was 34.75
against the published reference of 20.43. Its six-cell public result was
**−4.35**, versus **−25.44** for the published starting algorithm on those same
six cells, a gain of **21.09** points. The published reference is a different
provenance from repeated same-host measurements. It is useful to audit the
distribution of gains, including any floor effects, separately from the raw
absolute score. See `evidence/runs/claude-formal-vs-official-reference.json`.

## What we want back

1. **Audit the current loop.** Cite at least two specific code locations and
   two real run records. Identify what the code already does, what is missing,
   and what can be removed to make each decision easier to verify.
2. **Design a preflight that the Harness can call.** Cover target Python 3.8
   compatibility, official source/signature validation, loss and decoder
   behavior on tiny synthetic inputs when runtime dependencies and approved
   interfaces are present, and structured failure reporting. Separate fatal
   contract failures from advisory signals about mechanism strength. State
   which tests can run in the official Agent and which belong only in
   development. Use the official safety boundary for candidate execution.
3. **Propose the evidence and plan schemas.** Show an example for a decision
   after round 3, including parent, mechanism IDs, matching prior evidence,
   target cells, gains to protect, predicted behavior, and a falsifier.
   Provide a bounded data-selection policy that handles missing or conflicting
   receipts. Put code-generated comparisons ahead of model interpretation.
4. **Design the first four experiments and the remaining budget.** Start with
   comparable, isolated changes when possible. In round 4, choose a verified
   combination proposal or a missing control according to evidence. Show
   how it would handle compatible changes, two changes competing for the
   same code path, and a candidate whose gain is driven by one seed.
   Explain when to test a pair, three-way combination, or a removal, and when
   to stop. Every accepted physical experiment must fit the official budget.
5. **Give an implementable revision and verification plan.** Name the
   smallest useful changes, their tests, deployment dependencies, and the
   plan for a matched-budget GPU comparison. Include replay of an exact
   timing duplicate, a concentrated regression, an interaction conflict, a
   syntactically legal candidate that fails a probe, and a failed optional
   feedback parser after a successful official evaluation.

Read [Experiment protocol](EXPERIMENT_PROTOCOL.md) and
[Research notes](RESEARCH_NOTES.md) next. See [Bundle map](BUNDLE_MAP.md) for
the relevant source files, controls, and run artifacts.
