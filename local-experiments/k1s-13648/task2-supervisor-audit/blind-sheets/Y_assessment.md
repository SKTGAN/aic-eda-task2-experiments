# Run Y: blind assessment from rounds 1–2

Written 2026-11-19 from `BLIND_R2_ONLY.zip` (sha256 `0e0ab646…8d01`), folder `Y/`, before any later
record of this run was opened. Every number below comes from `Y/round-0{1,2}/{generation.json,
candidate.py, receipt.json}`. "Event n" refers to `generation_events[].sequence`.

## Provenance and contamination (read first)

- The receipts name the run: `overview.run = "10820-branching"`.
- My persistent memory from earlier reviews holds host-level facts about the team's 4090-era fleet,
  which includes this port. I did not use them below. The host fact used here is derived from this
  window alone, from the bp-ng45 cells.
- A pasted report from another session, with its own round-3 recommendations, reached this
  conversation before this sheet was saved. My choice of round 2 as the same-host parent was
  already in my working notes, but treat the overlap as non-independent.

## 1. What happened in each round

### Round 1: request `e-08344cd5…`, evaluated 18 Nov 04:21–06:10 UTC

- **Parent:** the official start (`parent_id 1a194e1a…32cc`). It is the same source text as run X's
  start (sha256 `8f87b6da…8aff`). Reason recorded: `opening_control`, component `decoder`, intent
  `decoder_only`. Why the decoder opens first is not recorded: **unknown**.
- **Main call `46eca52f…`** (effort low) received:
  - the generation system prompt, which ends with a 165-unit Chinese expert section (离线专家知识).
    It warns, among other things, that a loss change which does not reorder groups near the area
    cut may leave the tiers unchanged, and that whole-die flips must be counted separately from
    local boundary reordering;
  - the start program and nine cells. All feedback fields were null or empty.
- **Alternative calls:**
  - `40859db3…` and `6d878b98…` each produced a loss edit under a decoder-only intent. Both were
    rejected with "Keep the other function unchanged for this paired search direction" (events 5
    and 8).
  - Neither call received the expert section, because it is not part of `official_interface`.
- **Review call `ac321854…`** received only proposal A and returned "PICK A" (event 11). The
  opening comparison had no second candidate.
- **Explicit prediction** (docstring):
  - "this reorders only groups near the area median and should improve combined timing when the
    parent rounding left the final partition off the area target";
  - Falsifier: "matched-case combined score fails to improve while labels and timing-weighted cut
    remain unchanged."
- **Code:** `candidate.py` lines 32–73.
  - Area-weighted Lloyd iterations, then an area-quantile cut on the discriminant.
  - The low-projection side is labelled as the top die (line 72). The code itself chooses which die
    is top, and that choice is arbitrary.
  - It implements the docstring.
- **Receipt:** score 12.104, which is −8.321 against the published start. Labels by cell:
  - bp-ng45: 3 cells identical.
  - bp_fe/1003: 22 instances moved.
  - Five cells, bp_fe/1001, bp_fe/1002 and all three ariane cells, flipped every label. After
    undoing the flip, `flip_adjusted_changed_fraction` is at most 0.0097.
  - So all 9 cells kept the start grouping within 1%.
- **Per-cell results:**
  - The flips cost bp_fe −17.53, −14.65 and −16.33.
  - The flips gave ariane +15.82, −98.49 and +39.65. The −98.49 is ariane/1002: a raw −223 floored
    at −100, so the floor rule added 123.22 points.
- **The host does not reproduce the published start.**
  - The three bp-ng45 cells kept identical labels yet scored +0.28, +5.48 and +10.90 against the
    published values. They were flagged in `timing_changes_with_identical_assignment`.
- **Verdict:** the falsifier is ambiguous, because it counts a die flip as changed labels. Read up
  to the flip, nothing was regrouped and the score fell.

### Round 2: request `e-8a52cccc…`, evaluated 18 Nov 06:12–08:02 UTC

- **Parent:** the official start again. Reason recorded: `complementary_opening_with_first_receipt`,
  component `loss`. This follows the prompt ("Both openings start from the supplied official
  initial program"). The code that schedules it is not in the window.
- **Main call `fe4adcf8…`** (effort low) had no expert section. It received:
  - `decision.evidence`, `incumbent_feedback`, `decision_evidence` and the full `last_trial`
    (per-cell rows and `parent_comparison` with per-cell `assignment.flip_adjusted_changed_fraction`);
  - `prior_trials`.

  Three of the summary fields were misleading:
  - `gains_across_seeds` reported "bp-ng45 improved 3/3, worst +0.278". Those are the identical-label
    host cells.
  - `decision_evidence.parent_effect.all_labels_flipped_cells: 0`, although 5 cells flipped all but
    under 1% of their labels.
  - `prior_trials[0].inert_evidence: null`.

  The same brief also listed those bp cells under `timing_attribution_unconfirmed`, so the request
  contradicts itself.
- **Alternative `c1adf0ab…`** received the same brief as `evidence_brief` and proposed a
  slack-criticality weighting. **Review `54276de7…`** picked A, arguing that the graph term "can flip
  labels only when those embeddings cross its distance boundary", but it never checked the term's
  size.
- **Explicit prediction** (docstring):
  - "matched-case combined timing should improve where timing-weighted cuts are reduced, with labels
    changing near decoder decision boundaries";
  - Falsifier: "matched-case combined score fails to improve while timing-weighted cut and decoder
    assignments remain unchanged."
- **Code:** `candidate.py` lines 24–32 add `0.75 * sum(softplus(-graph_scores) * w) / sum(w)`; the
  decoder is the reference. This is the same term family as run X's round 1.
- **Receipt:** score 23.082, which is +2.657 against the published start.
  - Five cells kept identical labels: bp_fe/1002, bp_fe/1003 and bp ×3. The bp_fe pair matched the
    published values exactly. The bp cells repeated round 1's values bit for bit.
  - The other cells moved 1 instance (bp_fe/1001), 11 (ariane/1001), 164 (ariane/1002) and 10
    (ariane/1003).
  - The term raised `tp_gnn_final_loss` by 0.234 to 0.236 against round 1, which used the parent
    loss. That is about 0.55% of the loss, or 0.31 per unit of coefficient, so the term sat at its
    floor again.
  - The +2.657 decomposes, in summed cell points, into three parts:

    | Source | Summed cell points | Official mean |
    |---|---|---|
    | bp host differences on identical labels | +16.66 | +1.85 |
    | One moved instance on bp_fe/1001 | −27.28 | −3.03 |
    | ariane cells, against a start never measured on this host | +34.54 | +3.84 |

## 2. Biggest problem: the Harness's comparison step, example bp-ng45/1003

- **Step that went wrong:** the Harness left the measured same-host start out of the request and put
  a misleading substitute in its place.
- **The cell:** bp-ng45/1003 kept the start labels in both rounds. It scored −3.56 on this host both
  times, against the published −14.45. Yet it is counted as a +10.90 improved pair
  (`improved_pairs 5`, median +0.278) and summarised as a robust gain ("gains_across_seeds bp-ng45
  3/3").
- **Where the misleading summary went:** to the model in `fe4adcf8`, to the alternative in
  `c1adf0ab` and to the review in `54276de7`.
- **The broader consequence:**
  - The run's headline that round 2 beats the start rests on +34.54 ariane points measured against
    a baseline this host was shown not to share for bp.
  - Round 1's −8.32 mixes real bp_fe flip losses with that same unanchored ariane baseline. Its
    bp_fe losses (−48.5 summed) are real, because bp_fe reproduces the published values on this
    host.
- **Where the Harness could misjudge:** it could treat round 2 as a measured gain and ask for a
  "targeted repair" that protects the ariane cells and repairs bp_fe/1001. Both responses come from
  moving 1–164 instances, so that would chase noise.

## 3. One intervention for round 3

- **Decision:** a dose test of round 2's own term, from round 2.
- **Parent:** round 2, `candidate_id 057940f3…`, `verified_source_sha256 87f5d2e7…e564`.
  - All nine of its cells are measured on this host, so every round-3 delta is a same-host
    comparison.
  - Its grouping equals the start's within 0.13%.
  - I choose it as the measured baseline, not as a proven gain.
- **Search intent:** `loss_only`.
- **What changes:** one request field, `supervisor_note`, placed after `decision`, plus the parent
  override. Alternatives and review add nothing to a one-number dose test, so they are skipped.
- **Records the executor leaves:**
  - `supervisor_note` in the `model_request` payload;
  - `decision.reason = "supervisor_dose_test"` with the note's sha256;
  - `parent_source` set to the round-2 receipt in the round-3 `parent_comparison`.

Exact message:

> Supervisor note for round 3, from this run's receipts only.
> (1) The published start is not this host's start. bp-ng45 kept the start labels exactly in both
> rounds and scored identically on this host both times, yet +0.28, +5.48 and +10.90 above the
> published values. bp_fe-ng45/1002 and /1003 kept the start labels and matched the published
> values exactly. ariane133-ng45 has no start-label measurement on this host. So the bp-ng45
> "gains across seeds" and every ariane133-ng45 delta against the published start are not edit
> effects.
> (2) Neither opening regrouped. Round 1 kept the start grouping on all nine cells within 1% after
> undoing a whole-die flip and flipped five cells. Round 2's term moved at most 164 instances
> (0.13%) on any cell and raised tp_gnn_final_loss by only 0.23 to 0.24, about 0.55% of the loss
> and about 0.31 per unit of its coefficient.
> This round tests whether round 2's own term moves the area cut when it is large. Edit the
> supplied round-2 parent: change the term's coefficient from 0.75 to 20 and change nothing else,
> keeping the reference decoder call. Do not target individual cells. In the docstring, state that
> the term should add about 6.3 to tp_gnn_final_loss (about 15% of the loss), about +6.0 over
> round 2, and predict that at least 6 of
> 9 cells move at least 1% of instances after undoing any whole-die flip, with timing_weighted_cut
> lower on most cells that move. Judge timing against the round-2 parent's cells, which were
> measured on this host. If the loss rises as stated but fewer than 6 cells move, the hypothesis is
> false.

**Extra model calls:** none, and two fewer than the usual alternative-plus-review. A validator retry
would add one.

**If the budget is short:** send only the proposal call. If even that is unaffordable, keep round 2
as the incumbent and do not spend the evaluation.

## 4. How round 3 is judged (fixed in advance)

**Delivery:**
- The source differs from round 2 only in the coefficient.
- The loss rises by about 6.1 ± 0.5 against round 2 on every cell. If not, the intervention failed
  at the request step and says nothing about the mechanism.

**Mechanism, the metric expected to change:**
- At least 6/9 cells have a flip-adjusted moved fraction of at least 1%. Round 2's largest was
  0.13%.
- Whole-die flips are reported separately.
- `timing_weighted_cut` falls against round 2 on most moved cells.

**Score:**
- I predict no direction.
- A round-3 delta on ariane cells is a same-host comparison only against round 2, never against
  the published start.

**Protect:**
- Round 2 (23.08) stays eligible for final selection.
- bp_fe/1002 (49.93), bp_fe/1003 (55.82) and the bp start-label values (−20.55, −24.49, −3.56) are
  the existing results most at risk. A bp_fe case-mean loss of more than 10 points is a cost that
  must be reported, not netted away.

**Side effects:**
- The embeddings may collapse further.
- The reference decoder may flip dies.
- Floor effects of the ariane/1002 kind, the −100 clip.

**Withdraw the recommendation if any of these happens:**
- The dose is delivered but fewer than 6 cells move. The term is saturated, so change the mechanism.
- Cells move but `timing_weighted_cut` does not fall.
- Cells move and all three case means fall below round 2.
