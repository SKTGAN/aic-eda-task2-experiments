# Claude audit request: rolling ablation and protected improvements

Please audit the attached EDA Harness and propose a concrete, testable patch.
The central question is what the Harness should do **after any completed
evaluation**. Use all relevant earlier experiments available in the current
run to identify what is actually helping, protect measured gains when making
the next change, and improve weak designs without losing the gains elsewhere.
There is no prescribed opening sequence or fixed round for recombination.

The Harness steers the contest model, DeepSeek, to edit two allowed functions:
`compute_tp_gnn_loss` and `decode_tp_gnn_embeddings`. One scored evaluation is
three training designs by three seeds. The official run has at most ten
candidate evaluations and RMB 15 in model usage. Keep the official model,
starting program, evaluator, scoring, and budget interface. Select final
output by the official complete training matrix. Public validation occurs
after selection and must not feed the live search. Historical cross-run
artifacts in this bundle are for design and offline replay. The live search
compiles evidence from its own permitted training receipts.

## The failures we want the patch to address

| Observed problem | What the evidence shows | What an improved decision would establish |
|---|---|---|
| A local repair destroys valuable gains elsewhere. | Our evidence-driven round 4 improved the target `bp_fe-ng45/1001` by **16.42** points. Two strong `ariane133-ng45` seeds lost **16.86** and **30.68**. The official aggregate moved **26.49 → 25.01**. | Declare the weak groups and protected gains separately before generating code. Evaluate all nine groups. Check if the change actually repaired the target and how much it harmed other observations. |
| Two independently beneficial changes interfere. | On the same local `bp_fe-ng45/1001` cell, start **15.77**, hard-negative margin only **50.46**, tier swap only **52.65**, exact composition **28.37**. Its measured score interaction is **−58.96** points. | Reuse compatible controls where present. Measure a conditional contribution with a matched removal or addition. Preserve a good singleton or known parent if the merge loses. |
| A new source file can reproduce an earlier physical outcome. | Original Claude round 6 had identical WNS, TNS, and scores to round 4 for all nine cells. Rounds 5–10 all used round 4 as parent. | Use measured duplicate outcomes and mechanism fingerprints to choose a different question or parent. Timing duplicates alone do not establish identical assignments. |
| Feedback can be both verbose and fragile. | Our evidence-driven round 4 sent about 27,000 characters of user-side values with repeated key observations. The fourth matrix succeeded, then optional assignment analysis failed on `int.bit_count()` in Python 3.8. | Compute facts once, retain evidence IDs and precedence, assemble a compact packet, and save official scores before enrichment. Implement cheap checks in the actual Agent runtime; optional diagnostics should fail independently. |

The original Claude champion had training **34.75** and public **−4.35**.
The published starting reference on the same six public cells was **−25.44**,
so this public result was an improvement of **21.09** points. Public outcomes
and old run measurements are included for retrospective evaluation only.

## Questions to answer with code locations and test cases

1. **How should each next round plan its ablation?** Given all earlier receipts,
   how should code identify an exact measured control, distinguish a bundled
   change from an isolated mechanism, or determine which missing counterpart
   is worth one official slot? Show what the agent does when A helped alone
   but hurt alongside B, and when a low-scoring candidate has a useful
   mechanism for a weak case.
2. **How should it protect existing strengths and improve weaker designs?**
   Propose an evidence structure with explicit paired cells, WNS/TNS deltas,
   assignment state, evidence strength, and possible confounders. Given a strong
   parent and a proposed intervention, show a testable goal for the weak groups
   and a protection condition for supported gains. Explain what happens if the
   target improves but a previously strong group regresses. Use case and seed
   IDs as evidence labels only; generated algorithms must not dispatch on them.
3. **What can the Harness actually self-test?** Separate code contract and
   Python 3.8 checks, small synthetic behavioral probes, and real physical
   ablations through the official interface. Identify the available APIs and
   missing dependencies. Propose bounded repair after a failed preflight.
   Explain how the Harness could write its own proposed test on paper while
   a trusted fixed runner validates and executes only allowed checks.
4. **How does the model get the right amount of evidence?** Use deterministic
   code to search all eligible current-run history, while sending only
   decision-relevant comparisons. At a hard branch, ask an explicit
   higher-effort planning call to distinguish competing explanations and
   specify an experiment. Show exactly what is handed to code generation.
5. **What is the smallest patch that changes decisions?** Build an ordered
   implementation around the branching source and consider borrowing the
   two-stage planner. Include proposed function interfaces, a ten-slot
   budgeting rule that can replan every round, and acceptance tests on the
   attached historical cases. Separate replay decisions from new physical
   outcomes. Give a matched-budget plan to measure improvement over the
   current Harness.

Please return a short audit plus a patch or implementable pseudocode, with
file/function names, examples of the planner input and output, and a list of
failure modes. We are looking for an autonomous experimental loop, not an
increase in prompt length or a fixed round schedule.

Read [Rolling protocol](ROLLING_PROTOCOL.md), [Research notes](RESEARCH_NOTES.md),
and [Bundle map](BUNDLE_MAP.md). A small read-only comparison prototype is
under `evidence/rolling-audit/`.
