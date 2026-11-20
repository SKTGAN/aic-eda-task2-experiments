# Rolling ablation, feedback, and self-tests

This protocol is a proposal for the Harness, with example outcomes from the
enclosed real evidence. It is not a claim about future GPU scores.

## Decision after every evaluation

1. **Persist.** Save the official result, score, selected candidate and raw
   per-cell records first. Compute optional diagnostics afterwards, with
   independently logged errors. An incomplete cell remains missing, not zero.
2. **Index.** Index all prior candidates from the current run by code hash,
   parent and exact mechanisms and coefficients. Retain test scope, device or
   reference provenance, cell measurements and validation status. Compare the
   same design and seed in a comparable environment. Use a canonical
   representation to find possible duplicates, but verify exact function
   changes before treating two candidates as an ablation pair.
3. **Diagnose.** Choose an anchor for the next experiment and compute its
   gains and weak points against its measured parent or a clearly labeled
   published reference. Surface WNS/TNS separately from clipped score and
   distinguish a full die swap, local changes after area repair, and unchanged
   or unknown assignment. Propose two competing explanations when the data
   support more than one. A synthetic or partition-only diagnostic can weigh
   the mechanism explanation but cannot stand in for physical timing.
4. **Find a control or choose the next test.** Reuse an exact measured
   counterpart from anywhere in the current run. If the proposed contrast
   already exists, analyze it without consuming a slot. If it is missing, ask
   whether a remove-one, add-one, or alternative-control test would affect the
   next decision. Favor it over another speculative edit when it can resolve
   a choice such as keeping a factor or replacing it. If nothing important
   remains uncertain about the anchor, refine a weak point or try another
   distinct parent.
5. **Generate, validate, measure, repeat.** Pass a compact plan and only
   required evidence and source to the generator. Verify the intended diff,
   run eligible cheap checks, then submit through the official interface.
   Compare the outcome to the declared plan, record the next conclusion, and
   reassess the remaining budget. Scored combinations and ablations each
   cost one official candidate slot.

### Conditional effects, not a vote across variants

For anchor `P+A+B`, the actual contribution of A in that composition is
`score(P+A+B)-score(P+B)`, where the decoder, B, parameters, and the measured
condition stay fixed. Likewise, `score(P+A+B)-score(P+A)` measures B in that
context. A factor that helped against P can hurt in a combined program. With
all four matched settings, also compute `AB-A-B+P` per cell. Show raw WNS and
TNS, floor effects, design/seed stability, and missing controls separately.

The local example in this bundle demonstrates the difference. Added to P,
A and B gained about **34.69** and **36.88** points separately. Within AB,
both conditional effects were negative (**−24.27** for A with B and
**−22.09** for B with A). AB still beats P, but either singleton is stronger.
This is one observed cell, not a rule about all loss or decoder changes.

When variant A and B edit the same function in competing ways, or a new
candidate changes coefficients at the same time, do not infer an exact
factorial contrast. Design a clearly labeled merged intervention or obtain an
isolating control. For repeated assignments or changed timing across hosts,
carry forward the uncertainty and seek a matched same-host comparison if it is
valuable and eligible.

### Repair the weak point while preserving strengths

- Separate a **search anchor** from the **final official champion**.
  Choosing a lower-ranked parent to learn about a complementary mechanism
  does not discard the champion.
- Carry a compact list of protected observations with evidence IDs and reasons
  (e.g. repeatable multi-seed gains or a design whose TNS benefit must be kept).
  Specify the weak observations and the predicted behavior through the loss,
  embeddings, tier repair, and final WNS/TNS when the evidence supports it.
- Before generation, define what would count as improvement and what loss on
  protected cells would disprove the plan. Do not change the criterion after
  seeing the result. Group the protection logically by design and seed.
  A tolerance or repeatability check must be explicit, preferably calibrated
  by matched repeat measurements. Protecting a single noisy cell with an
  arbitrary zero tolerance is a policy choice for review, not a scoring rule.
- After the nine-cell result, compare the weak and protected groups as well
  as the official total. When a target improves but protections fail, retain
  the best complete candidate and ask whether a removal or conditional change
  is more informative than another free-form tweak. Official final ranking
  still uses the official score.

### Compact packet for the model

The full archive stays available to deterministic code. One possible packet
contains a nine-row paired summary for the anchor and latest candidate, two
or three historical comparisons with provenance and source IDs (same
mechanism, matched control, or counterexample), one planned edit, and a
protected-gain/weak-cell checklist. Use exact source only for the selected
parent and the component being tested. The planner should identify the
one comparison a new run adds, alternative explanations, and a falsifier.
The generator gets the checked plan with evidence IDs and protected
conditions, rather than multiple copies of the same previous receipt.

## Scope of self-testing

| Layer | What the Harness can test | What it establishes |
|---|---|---|
| Static | Official source validator, permitted function boundaries, source diff, Python 3.8 feature/stdlib checks, plan-to-patch consistency | Eligibility for execution and the intended intervention |
| Small synthetic, if supported in the official Agent | Loss returns a finite scalar and finite gradients on bounded inputs; decoder returns legal binary labels and balance under the actual contract; deterministic behavior for a fixed synthetic seed | Correctness and observable mechanism behavior on the fixture only |
| Retrospective replay | Archive joins, exact same-condition contrasts, handling of duplicate timings and incomplete feedback | Correctness of the Harness decision logic on observed prefixes |
| Official evaluation | Matched anchor/addition/removal under the real design and all three seeds using the official bridge | Measured effect on the scored grid and its interaction with other mechanisms |

Treat identical results on toy inputs as advisory unless the checked property
is a true contract requirement. Make the probe optional if the official Agent
does not expose the needed runtime or API. Never create an unmetered physical
evaluation path. Synthetic fixtures, real training cases, old development logs
and the held-out public set have different permitted uses.

At any point, spend a remaining slot on the question most likely to change
the next decision. Keep enough capacity for at least one follow-up when
proposing a high-uncertainty merge late in a run, when the official budget
allows. Use the official API to check remaining slots and model budget. If a
comparison has no matching receipt and no slot remains, mark it untested.

## Minimum acceptance cases for the proposed patch

1. A measured removal from an early round is found after many later rounds
   and consumed as evidence without resubmitting it.
2. A missing or incomparable control is surfaced as a new experiment
   suggestion, not counted as an effect. A multi-factor bundled diff is not
   credited to an individual factor.
3. The exact same-host AB fixture rejects additive interpretation and
   preserves the stronger singleton. The nine-cell offspring fixture flags
   a target gain alongside two protected regressions.
4. A manifest mismatch, invalid labels, NaN loss, and target runtime failure
   each produce useful diagnostics. An unavailable probe is explicitly
   skipped, and optional post-evaluation failures preserve the official score.
5. Under the same ten-candidate budget, report best complete training scores
   by accepted slot, duplicate physical outcomes, validity and repair rates,
   total model cost and latency, completed ablations, and public validation
   of the selected result. Replay cannot measure unrealized candidates'
   physical performance, so report it separately from matched live runs.
