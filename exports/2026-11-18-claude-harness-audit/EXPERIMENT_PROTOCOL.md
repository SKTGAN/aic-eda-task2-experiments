# Proposed experiment and preflight protocol

This is a design for review. The enclosed measurements are real; the candidate
allocation and online checks below have not been validated on a new contest run.

## Before spending a physical evaluation

| Stage | Deterministic work | What a failure means |
|---|---|---|
| Reference and history | Archive raw receipts with source hashes and effective lineages. Join same design and seed under the same evaluation scope. Mark whether a comparison uses a published reference or a measured parent. Store physical floor effects, assignment status, and measured WNS/TNS. | Missing, incomparable, or contradictory measurements remain unknown. They do not imply a zero effect. |
| Plan | Pick a measured parent when available. Record one identified intervention or a declared composition of previously identified interventions. Record which valid observations to improve and which to protect. Ask a high-effort planner for competing explanations at a branching decision or after a failed combination. | If a plan names no intervention that would change a result, ask once for a testable alternative. |
| Static gate | Run the official validator on the complete program. Check target Python syntax and runtime APIs separately. Confirm the intended loss and decoder boundaries by normalized diff. Compare exact or normalized source fingerprints to avoid spending a slot on the same candidate. | Contract, version, and undeclared edit failures block submission pending bounded repair. |
| Bounded synthetic probe | Only when verified available in the official Agent runtime, use tiny fixed fixtures and approved execution interfaces. For loss, check a finite scalar, backward pass and finite gradients on expected tensors, with empty/tied edge cases where legal. For decoder, check shape, integral binary labels, deterministic output at fixed seed, and area legality using the official constraint contract. Bound execution time and memory. | A broken invariant blocks submission. Same labels on hand-made fixtures or a small proxy change is advisory. A legitimate loss can change trained embeddings without affecting a decoder-only fixture. Missing dependencies are reported as unavailable. |
| Submit and recover | Submit through the official bridge. Match receipts by request ID. Persist valid official scores and best candidate before computing optional diagnostics; continue with basic feedback if enrichment fails. | Invalid code and infrastructure interruptions stay distinguishable from measured physical regressions. Use an official retry only if authorized and budgeted. |

The in-container probe must have no design or seed identity as a decision
input. Case and seed identifiers label evaluation evidence for the Harness
and must never dispatch hand-written algorithm behavior. Development-only
partition replay or reduced-panel evaluation can check mechanisms before a
new run, subject to the organizer's rules. These checks cannot create extra
scored evaluations during a formal run. A toy fixture or a proxy metric does
not establish timing improvement.

## Candidate attribution and composition

Start from one parent `P`. For an isolated mechanism `A`, record per-cell
`score(P+A) - score(P)`. Also store raw slack deltas, number of improved seeds,
the worst regression, assignment difference, and provenance. If two earlier
variants differed in multiple components, describe their evidence as a
bundle; use a paired reversion or matched control before attributing the gain
to one change.

For a merge, treat `P`, `P+A`, `P+B`, and `P+A+B` as a paired two-factor
contrast on the same design and seed. Compute
`interaction = score(P+A+B) - score(P+A) - score(P+B) + score(P)`.
In the capped scoring regime, also compute the contrast on available raw WNS
and TNS and report which scores hit the floor. A single-cell interaction
demonstrates interference on that cell; generalization needs the other
designs and seeds. Two alternatives replacing the same decoder, or two
interventions changing the same normalized term, need an explicit merge
plan or should be treated as competing alternatives. Keep declarations
and fingerprints for every factor. A new weighting strength or any extra
algorithm change creates a different experiment and invalidates an
otherwise matched four-cell contrast.

### An adaptive allocation within ten submissions

| Accepted candidate slots | Intended use | Change when evidence is weak |
|---|---|---|
| 1–3 | Test three distinct, isolated changes from a common parent. For example, use a loss intervention, a decoder intervention, and a clean alternative or control. | Prefer an indispensable matched control when an effect on the published reference is ambiguous and the official interface permits it. Count any accepted control against the budget. |
| 4 | Run one merge of complementary, separately measured changes from the common parent. | If the prior variants are confounded or incompatible, use this slot for a removal/control or a fresh isolated change. |
| 5–7 | Confirm the strongest proposed mechanism via a targeted removal, test a plausible alternative pair, or refine the most robust branch. | If the pair already lost to both singletons, examine its worst contrasting cells and preserve the best observed singleton. Avoid returning to a combination already refuted by complete comparable results. |
| 8–10 | Resolve remaining decision-relevant uncertainty. A three-way merge is an option after at least one informative pair; a matched leave-one-out variant can justify keeping or dropping the third intervention. | A fresh discriminating hypothesis is preferable to spending a slot on identical code. Allow early stop if the official interface or budget prevents a useful next experiment. |

This schedule screens mechanisms and selectively measures interactions. It
does not identify every three-factor interaction unless the corresponding
cells have been evaluated. All official candidate slots cover nine physical
cells. A published reference and a measured same-host parent have different
evidence strength. No assumption of free or privileged evaluation is needed.

## Isolate the Harness changes too

First compare the current branching Harness, a version with a single compact
evidence object, and a full suggested version using identical archived prefixes
and deterministic assertions. Add focused comparisons with planning held
fixed, preflight held fixed, or recombination disabled to learn which
controller features matter. Replay checks the decision and its inputs. It
cannot estimate the score of a never-generated candidate.

For live verification, first compare the strongest two complete variants
on the same task package, machine type, official model, training grid, and
budget, starting from the official program. If resources allow, repeat to
show run-to-run variance. Report best valid training score after 3, 6 and 10
submissions, public validation for the selected candidate only, accepted
and rejected proposals, duplicate physical outcomes, model call count and
cost, median model/planning wall time, and wall time per successful matrix.
Keep request/response timings and measured token usage as separate fields;
record the requested reasoning effort without inferring internal reasoning time.
