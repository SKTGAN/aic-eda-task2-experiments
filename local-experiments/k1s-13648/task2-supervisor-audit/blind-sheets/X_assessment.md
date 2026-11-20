# Run X: blind assessment from rounds 1–2

Written 2026-11-19 from `BLIND_R2_ONLY.zip` (sha256 `0e0ab646…8d01`), folder `X/`, before any later
record of this run was opened. Every number below comes from `X/round-0{1,2}/{generation.json,
candidate.py, receipt.json}`. "Event n" refers to `generation_events[].sequence`.

## Provenance and contamination (read first)

- The receipts name the run: `overview.run = "22120-independent"`.
- My persistent memory from earlier reviews for this team holds host-level facts about port 22120
  (a 3090 host that reproduces the published start) and one later score of this run. I did not use
  them below; the host fact is re-derived from this window (R1: 6 cells with identical labels match
  the published values exactly).
- A pasted report from another session, with its own round-3 recommendations, reached this
  conversation before this sheet was saved. My reasoning about the parent and the loss edit was
  already written in my working notes before it arrived. The final wording may still be
  influenced, so do not score this sheet as an independent prediction.

## 1. What happened in each round

### Round 1: request `e-a79c1987…`, evaluated 18 Nov 01:26–03:56 UTC

- **Parent:** the official start (`parent_id 57ea753c…2643916`; sha256 of the supplied
  `parent_program` text is `8f87b6da…8aff`). Reason recorded: `opening_control`, intent `loss_only`
  (events 1, 3, 5). Why the opening edits the loss rather than the decoder is not recorded:
  **unknown**.
- **Planner call `388de9e6…`** (effort high) received:
  - the system prompt with field notes and the English Offline Expert Knowledge section (66 units):
    "Weak terms can leave boundary labels fixed. Fewer cuts can worsen timing. Separate die swaps
    from regrouping. Compare matched seeds and both slacks; a single-cell gain may not hold.";
  - the parent program, the nine training cells, and `evaluations_remaining 10`. All feedback
    fields were null or empty.
- **Coder call `a346f09d…`** (effort low) received the generation system prompt, which has no
  expert section, plus the planner's `experiment_plan`, an empty `prior_trials` and a null
  `largest_regression`. The coder never saw the expert note.
- **Explicit prediction** (plan, event 2):
  - "Expect better TNS via lower timing-weighted cut, with neutral/risky WNS."
  - Falsifier: "a matched case/seed shows no combined gain or unchanged labels with timing-only
    change."
- **Code:** `candidate.py` lines 32–44 add
  `0.5 * sum(softplus(-graph_scores) * graph_weights) / sum(graph_weights)` to the unchanged pair
  term. The decoder is unchanged (line 54). This is what the plan described.
- **Receipt:** score 5.473, which is −14.952 against the start's 20.425.
  - Six cells kept the start labels exactly. Their timing equals the published values to the last
    digit, so this host reproduces the published start on those cells.
  - Three cells moved a few instances, and all three lost points:

    | Cell | Instances moved | Score change |
    |---|---|---|
    | bp_fe/1001 | 1 | −27.28 |
    | ariane/1002 | 81 | −12.62 |
    | ariane/1003 | 10 | −94.66 |

  - `improved_pairs` was 0.
- **Size of the added term** (derived from the receipts; never shown to the model):
  - Round 1's `tp_gnn_final_loss` minus round 2's (round 2 kept the parent loss) is +0.155 to
    +0.158 on every cell. That is 0.36–0.39% of the loss.
  - Per unit of coefficient it is 0.311–0.315, which is softplus(−1). The star edges were already
    aligned, so the term sat at its floor.
- **Verdict:** falsified on the plan's own terms. No matched cell gained, and 6 of 9 cells kept
  their labels.

### Round 2: request `e-69980d14…`, evaluated 18 Nov 03:59–06:25 UTC

- **Parent:** the official start again. Reason recorded:
  - `test_alternative_component_after_opening`, with evidence `partition_mostly_unchanged`
    (6 identical, `kept_up_to_swap` 8, `die_swaps` 0);
  - `largest_regression` ariane/1003 at −94.66 (meta and event 15).
  
  The prompt says "Only a broad gain becomes the parent", which fits this choice, but the
  selection code is not in the window. The exact rule is **unknown**.
- **Planner call `838541b1…`** (effort high) had no expert section this time. It received:
  - `incumbent_feedback`, holding round 1's nine rows: score, WNS, TNS, `cut_net_count`,
    `timing_weighted_cut`, `tp_gnn_final_loss` and the partition-change flags;
  - round 1's `parent_comparison`, whose cut deltas are null on the three moved cells;
  - `prior_trials`;
  - `start_reference`: 6 same-host cells, 3 published, 20.425, `mixed_reference`.

  `parent_feedback` was null, so the parent's own loss and cut never reached the model. The field
  note "the change in `tp_gnn_final_loss` from the parent approximates the term's size" therefore
  could not be applied.
- **Coder calls:**
  - `429f442c…` (effort low) received only the plan, the decision, `prior_trials` and
    `largest_regression`. It got no per-cell rows. Its reply was rejected with "Unsupported NumPy
    operation: zeros" (event 12).
  - The retry `8a930892…` carried `previous_generation_issue` and was accepted (event 15).
- **Explicit prediction** (plan, event 9):
  - "select B because A produced 6/9 identical … B should improve TNS by separating
    timing-coupled embeddings, with WNS neutral."
  - Falsifier: "any valid case, especially ariane133/1003, with unchanged labels or TNS
    regression."
- **Code:** `candidate.py` lines 50–102.
  - It projects onto the largest-variance coordinate and splits by cumulative area.
  - It then alternates area-weighted centers, a projection on c1−c0, and an area-cumulative split.
  - It labels the higher-projection side as the top die. That choice of top is arbitrary relative
    to the reference.
  - The loss is unchanged. The code implements plan B as written.
- **Receipt:** score 23.420, which is +2.995.
  - Three cells kept identical labels. Six exchanged the dies, with `moved_fraction_up_to_swap`
    between 1e-5 and 0.019. `kept_up_to_swap` was 7.
  - Score change on each of the six swapped cells:

    | Cell | Score change | Moved after undoing the swap |
    |---|---|---|
    | bp_fe/1001 | −10.36 | 0.96% |
    | bp_fe/1003 | −0.95 | 1.9% |
    | bp/1001 | +10.60 | |
    | bp/1002 | −21.98 | |
    | bp/1003 | +4.83 | |
    | ariane/1003 | +44.81 | 2e-5 |

  - ariane/1003 alone is worth +4.98 on the official mean. The other eight cells net −1.98.
  - The plan's own falsifier was triggered. Three cells kept their labels. TNS got worse on
    bp_fe/1001 (−174.7 to −314.5 ns) and bp/1002 (−10349.9 to −12781.9 ns).

## 2. Biggest problem: round 2, ariane133-ng45/1003

- **Step that went wrong:** the code implemented the proposal as intended, and the evaluation
  contradicted the proposal's mechanism. Yet the score went up, which hides the contradiction.
- **The plan claimed** that a custom two-center loop would move groups across the area boundary
  ("separating timing-coupled embeddings").
- **The receipt shows** the start grouping kept on 9/9 cells up to a die exchange (at most 1.9%
  moved), with ariane/1003 at 2e-5.
  - Its +44.81 comes from exchanging the dies. It is the run's largest positive cell and exceeds
    the round's whole net gain.
  - The same cell lost −94.66 in round 1 when only 10 instances moved. This cell swings tens of
    points on changes that are not regrouping.
- **Contributing cause on the Harness side** (evidence omitted):
  - The round-2 planner had two competing explanations for round 1's unchanged labels: a weak
    term, or a rigid decoder.
  - The one number that separates them is the parent's own `tp_gnn_final_loss`. It was not sent
    (`parent_feedback: null` in `838541b1`).
  - The model chose the decoder explanation. After round 2 the answer is in hand: decoder variants
    reproduce the grouping, and the term was 0.37% of the loss.
- **Where the Harness could misjudge:** it could credit +2.99 as a decoder gain and promote round
  2 as parent. Any later loss edit would then re-roll that decoder's arbitrary choice of top die on
  every cell.

## 3. One intervention for round 3

- **Decision:** a dose test of the round-1 term, using the program that already contains it.
- **Parent:** round 1, `candidate_id ebbb7303…`, `verified_source_sha256 a45fcefd…52ff`. Its
  nine cells were measured on this host, and it differs from the start only by the term.
  - Round 2 (23.42) stays eligible for final selection.
  - The start would also work as the parent, since this host reproduces it on 7/9 checked cells.
    But the coder would then have to rebuild the term from a 200-character description.
- **Search intent:** `loss_only`.
- **What changes:** one new request field, `supervisor_note`, in the planner and coder requests,
  plus the parent override.
- **Records the executor leaves:**
  - `supervisor_note` inside both `model_request` payloads;
  - `decision.reason = "supervisor_dose_test"` with the note's sha256 in the submitted event;
  - the coefficient and expected loss rise in the candidate docstring.

Exact message:

> Supervisor note for round 3, from this run's receipts only.
> (1) Round 1's edge term was too small to reach the labels. Compared with round 2, which kept the
> parent loss, it raised tp_gnn_final_loss by 0.155 to 0.158 on all nine cells: about 0.37% of the
> loss and about 0.31 per unit of its coefficient. Six cells kept the start assignment exactly;
> the others moved 1, 81 and 10 instances.
> (2) Round 2's decoder did not regroup. All nine cells kept the start grouping up to a whole-die
> exchange (moved_fraction_up_to_swap at most 0.019), and six cells exchanged dies. Its +2.99
> comes from the exchange on ariane133-ng45/1003 (+44.81); the other eight cells net -1.98. It is
> not evidence for a decoder mechanism.
> This round tests only whether the round-1 term moves the area cut when it is large. Edit the
> supplied round-1 parent: change the term's coefficient from 0.5 to 20 and change nothing else,
> keeping the reference decoder call. In the docstring, state that the term should add about 6.3 to
> tp_gnn_final_loss (about 15% of the loss), about +6.1 over round 1, and predict that at least 6 of 9 cells move at least 1% of
> instances after undoing any whole-die exchange, with timing_weighted_cut lower on most cells
> that move. If the loss rises as stated but fewer than 6 cells move, the hypothesis is false.

**Extra model calls:** none. The note rides on the existing planner and coder calls. A validator
retry, as in round 2, would add one.

**If the budget is short:**
- Drop the planner call and send the note to the coder alone.
- If no generation call is affordable, do not spend the evaluation, and keep round 2 as the
  incumbent.

## 4. How round 3 is judged (fixed in advance)

**Delivery:**
- The round-3 source differs from round 1 only in the coefficient.
- `tp_gnn_final_loss` rises by about 6.1 ± 0.5 over round 1 on every cell (term ≈ 6.3, against
  round 1's 0.157). If it does not,
  the result says nothing about the mechanism.

**Mechanism, the metric expected to change:**
- At least 6/9 cells move at least 1% after undoing any swap. Round 1 moved at most 0.062%.
- Any die exchange is reported separately.
- `timing_weighted_cut` falls against the parent on most moved cells.

**Score:**
- I predict no direction. There is no counterfactual round 3 to compare against.

**Protect:**
- Round 2 (23.42) stays the incumbent for final selection.
- bp_fe, the start's strongest case (mean 53.92), is the cost to watch: one moved instance
  already cost −27.28 there.

**Side effects:**
- The embeddings may collapse further.
- The reference decoder may exchange dies.
- bp_fe and ariane may swing by tens of points.

**Withdraw the recommendation if any of these happens:**
- The dose is delivered but fewer than 6 cells move. The term is then saturated rather than weak,
  and the next round should change the mechanism, not the dose.
- Cells move but `timing_weighted_cut` does not fall. The term then does not do what it claims.
- Cells move and all three case means fall below the parent.
