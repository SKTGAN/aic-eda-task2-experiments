# Supervisor audit: blind sheets against later rounds, cross-round supervision in K1, and a minimal supervised K1

All Task 2 material in this report comes from `Claude-Supervisor-Harness-Audit-41.73.zip`:
- the package sha256 checks pass on all 331 files;
- `verify.py` reproduces 33.912796, 34.394356, 39.680927 and 41.732793 and the 2/6 validation snapshot.

No new physical evaluation, model call or GPU run was made. "Replay" means the recorded R1/R2 candidates and official receipts were fed through the Agent code offline (`replay/replay.py`).

## The main question: what does the supervised Harness do differently in round 3?

**Run X's rounds 1–2 (22120-independent).**
- **Same input to both arms.** The loss opening scored 5.47, with 6 of 9 labels unchanged. The decoder opening scored 23.42 (+2.99), with the dies exchanged on 6 cells. Both arms send byte-identical requests in rounds 1–2.
- **Unsupervised K1** makes round 3 a `refine` of R2 (`refine_incumbent`, parent `203e2676…`).
- **The supervised K1 (K1S)** sets R2 aside as the round-3 parent:
  - 7 of R2's 9 cells are the official grouping or its exact inversion;
  - its 4 inverted cells give +38.26 summed points and the other 5 cells −11.31.
- **K1's own policy then picks the next step:** the official start as parent, `diversify`, and a required loss change.
- **The request carries one new field, `supervisor_note`**, stating that evidence and the size of R1's loss term: +0.155 to +0.158, 0.37% of the loss.
- **R2 stays eligible for final selection.** The adjustment lasts for that one step.

**Run Y's rounds 1–2 (10820-branching, in its own decoder-first order).** The supervisor keeps K1's decision. Both arms submit the shelved opening alternative without a model call.

Side by side: `examples/round3-side-by-side.html` and `.md`.

---

## 0. Order of work and what was blind

**1. My sheets were written first, from the two-round windows only.** They are in `blind-sheets/` and were hashed at 11:38 UTC, before the package was opened:
- `X_assessment.md`: `8acb6a7f089d…`
- `Y_assessment.md`: `4f0922017b5f…`

They are not clean blind judgments, for three reasons stated at the top of each sheet:
- the receipts name the runs;
- my memory from earlier reviews held host facts and one later score for X;
- your pasted report (the other session's sheets, below) arrived before I saved mine.

**2. The other session's sheets** are in `/root/code/blind-r2-review/`:
- `X_assessment.md`: `c18d48f0…`
- `Y_assessment.md`: `7ca8e80e…`

Both hashes match their `SHA256SUMS.txt`. Below, **A** means the other session's sheets and **B** means mine.

**3. Then the full package, then K1, then K1S.** The package brief (`START_HERE.md`) asks for eight answers in Chinese. I answered your five English questions in English and folded the brief's items into them.

---

## 1. The blind sheets against the later rounds

Scores for branches nobody ran are **unknown**. No later receipt tells us what the recommended experiment would have scored.

### Run X (22120-independent)

What happened after round 2:

| Round | Parent | Edit | Score | Labels (vs official start) |
|---|---|---|---:|---|
| 3 | start | loss: criticality alignment | 23.39 | moved on 9/9 cells: bp_fe 1.1–1.5%, bp 0.24–0.35%, ariane 1.8–23.7%; 0 swaps |
| 4–7 | start | decoder / loss / loss (star-edge term ×1.5) / decoder | 15.61, 2.79, 7.09, 3.76 | R4 and R7 exchanged dies; R6 was inert again |
| 8 | start | loss: criticality-weighted positive pairs | 25.58 | at most 0.23% moved |
| 9–10 | R8 | refine, then diversify | 32.09, **32.68** | R10 moved 12–30% on ariane; its ariane cells gained +32.1, +56.1 and +17.2 against R8 |

Claims in the sheets:

| Claim | Sheet | Later evidence | Verdict |
|---|---|---|---|
| R2's +2.99 is a die-swap artifact carried by ariane/1003 | A, B | X's own Harness classified R2 `orientation_only` and kept the start as parent for R3. The later decoder rounds R4 and R7 again exchanged dies and scored 15.61 and 3.76 | **Supported** |
| The Harness could promote R2 as parent | B | X's Harness did not, but **K1 would**: the replay shows K1 refining R2 | Supported for K1; **revise for X** |
| R1's star-edge term sat at its floor (0.31 per unit coefficient, 0.37% of the loss) | A, B | R6 reran the family at 1.5 and was inert again (5 cells identical) | **Supported**. A 1.5 coefficient is not a dose test |
| Biggest problem: R1 plan ignored the warning (A); R2 mechanism contradicted while the score rose (B) | A / B | Both are consistent with what followed. Neither was falsified | Keep both |
| Round 3: dose test of R1's term (A from the start at 10–20% of the loss; B from R1 at coefficient 20) | A, B | **Never run, score unknown**. The run found label movement another way: R3's node-feature term moved at least 1% on 6 of 9 cells in one round | **Revise**: the dose test was a narrower experiment than needed |
| Mechanism criteria: movement plus a lower `timing_weighted_cut` | A, B | X R3 met both (moved at least 1% on 6/9 cells; lower cut on 7/9) yet lost points on 6/9 cells, with median −11.14. Its +2.96 is one cell, ariane/1002 at +89.94 | **Revise B.** Movement and cut are necessary, not sufficient. B needs A's one-cell rule and a per-case timing criterion |
| Protect bp_fe | A, B | R3 lost bp_fe on all three seeds (−25.5, −12.8, −2.7) | **Supported** |

### Run Y (10820-branching)

What happened after round 2:

| Round | Parent | Edit | Score | Labels |
|---|---|---|---:|---|
| 3 | **R2** | decoder: micro-flips on the reference split | 25.35 | only bp_fe moved, by 0.07%. The +2.26 over R2 is bp_fe/1001 +18.57 (partly repairing R2's one-instance loss), bp_fe/1002 −5.06 and bp_fe/1003 +6.86 |
| 4–10 | R3, R4, R8 | loss reweighting (squared, cubic) and decoder micro-flips | 26.93, 24.67, 2.81, 23.85, **27.50**, 7.19, 23.23 | **never more than 0.30% moved** on any cell |

Claims in the sheets:

| Claim | Sheet | Later evidence | Verdict |
|---|---|---|---|
| bp "gains" against the published start are host differences | A, B | bp/1002 and bp/1003 kept the start labels and the same values (−24.49, −3.56) in all ten rounds. bp/1001 did the same (−20.55) whenever its labels stayed at the start (R1–R3, R7) | **Supported** |
| Use R2 as parent, because it is the only all-nine same-host baseline | A, B | Y's Harness also chose R2 (`extend_best`). From R3 on, every comparison is `run_evaluation`, so same-host | **Supported** |
| Neither opening regrouped; the term is saturated | A, B | From round 2 to 10, no candidate moved more than 0.30% of instances on any cell (round 1: at most 0.97%, once its inversions are undone). Squared and cubic edge weights (R4, R9) did not move labels | **Supported** (reweighting, not dose) |
| Biggest problem: R1's decoder was a die lottery (A); the Harness's framing against the published start (B) | A / B | B's framing problem went away once a measured candidate was the parent. The lasting problem was that nothing forced a regrouping mechanism, so eight rounds stayed below 0.3% movement | **Revise B's ranking** |
| Round 3: dose test of R2's term | A, B | **Never run, score unknown** | — |
| A's runner-up: an orientation-preserving decoder from the reference split | A | This is close to what Y actually ran in R3. It scored +2.26, but under A's own threshold (at least 0.5% on 5/9 cells) it is not a regrouping | A's ranking holds |

---

## 2. Does K1 provide cross-round supervision?

**No.** K1 has an opening-proposal review and a rule-based per-round step chooser. No role sees all four records together, and nothing reviews the execution strategy across rounds.

What each part of K1 does and sees (baseline line numbers in `baseline-K1/…/agent.py` and `search_policy.py`):

| Part | Where | What it sees | Can it change round 3? |
|---|---|---|---|
| Generation model | `agent.py:526–558` | The parent program and summaries of the parent, incumbent and two recent receipts, plus the ledger and the decision | It writes the program. It cannot change the parent or the intent |
| Opening alternative and review | `agent.py:591–628`; `review_opening` at `166–174` | The parent program, the interface and the proposals. **No receipts.** Runs only on `opening_control` steps, i.e. R1 and R2 | No |
| Search policy `next_step` | `search_policy.py:252–347`, called at `agent.py:445` | One `describe_trial` fact row per receipt. No requests, replies or diffs | **Yes**: it alone picks round 3's parent and intent |
| `check_proposal` | `agent.py:113–154` | The code of one proposal | It rejects proposals only |

**Which role sees all four records?** None:
- K1 does not log model requests or replies at all. The 34.75 run, K1's ancestor, has 0 recorded request and response bodies.
- No step reads diffs next to receipts.

**What the gap costs.**
- `classify` (`search_policy.py:118–147`) counts a whole-die inversion as an assignment change, because the changed fraction is 0.99, well above 0.1%.
- So R2 is "effective" and leads the start. Step 8 (`search_policy.py:342–347`) then refines it.

**The missing step.** It belongs between "round-2 receipt recorded" (`evaluate` → `record` → `evaluated`, `agent.py:416–419`) and "round-3 step used" (`agent.py:445`). That is where K1S's `supervise()` sits.

**A separate K1 defect found by the replay.**
- K1's decoder probe (`decoder_probe.py:30–31`) runs candidates with a 10-name builtins table.
- NumPy's lazy import inside `ndarray.mean` then raises `KeyError('__import__')`. The probe reports it as a decoder failure.
- With NumPy present, K1 rejects Y's real round-1 decoder, which the organizer evaluated without error.
- This matches the earlier `KeyError: '__import__'` seen in the 34.75 run's first round.
- `patches/shared-K1-probe-fix.diff` adds `__import__` to the probe's table, and the probe still detects parent-equivalent decoders. Apply it to **both** arms before any A/B; it is not part of the supervisor diff.

---

## 3. How the main conversation went from 33.91 to 41.73

All four versions ran on one RTX 4060 Laptop, nine cells each, same code per row. `verify.py` reproduces every mean.

| Version | Score | bp_fe | bp | ariane | Change |
|---|---:|---:|---:|---:|---|
| `capacity_quantum` | 33.9128 | 48.99 | −2.43 | 55.19 | capacity-quantum decoder |
| `variance_guard` | 34.3944 | 48.99 | −2.43 | 56.63 | ariane/1001 16.72 → 68.64, **ariane/1003 78.47 → 30.89** |
| `three_radius_guard` | 39.6809 | 48.99 | −2.43 | 72.49 | 1001 keeps 68.64, 1003 back to 78.47, the other seven equal |
| `coarse_majority` | 41.7328 | 55.14 | −2.43 | 72.49 | bp_fe −3.33, +15.92, +5.88; the other six equal |

### Decision 1: after variance_guard, the experiment that scored 39.68

**Known when it was chosen** (timeline 19 Nov 08:17, before variance_guard's last cell finished at 08:26):
- The paired split on ariane: +51.91 on 1001 and −47.58 on 1003. Net, it showed only as +0.48.
- The same-host rerun of Claude R4 on ariane/1001: 68.64.
- Per-cell cluster geometry from the archived same-loss embeddings:
  - variance_guard sent both ariane cells to the R4 branch (between/within ratios 2.78 and 2.15);
  - the three-radius test (centre distance at least 3 pooled radii) separates them: 3.33 goes to the R4 branch, 2.93 to the capacity branch.
- A label replay showed that every cell's new labels equal labels already measured on that machine. So 39.68 was predicted before the run ("九组分层回放对应的历史成绩均值是 39.68").

**Learned only after the run** (10:03, 10:23, 11:53):
- the physical results reproduced the predicted cells exactly (68.6366, 78.47, …).

**Still unknown:**
- why ariane/1003 prefers the capacity labels;
- whether a threshold of 3, which falls between two training cells (2.93 and 3.33), means anything on another design.

### Decision 2: after a better area balance gave worse timing, the experiment that scored 41.73

**Known when it was chosen** (13:12–13:51, and the branch audit before the run):
- `three_radius_adjacent` cut bp_fe/1003's area error from 34,580 to 5,320 by moving 6 instances. The score fell from 51.51 to 43.07.
- Equal-area reordering scored +5.29, −8.69 and −18.60 (mean −7.33).
- A flip control scored +4.08 on 1002 and −2.06 on 1001.
- An area census:
  - bp_fe has 9 supernodes holding **75.4%** of its area, each too large to move alone;
  - ariane and bp have none.
- `coarse-majority-branch-audit.json` computed the conditional score **41.7328 before the run**, from 16 Nov receipts of the official partition with dies swapped on bp_fe ("mirrored stock": 52.65, 55.38, 57.39).

**Learned only after the run** (14:23–16:11):
- the bp_fe cells reproduced those historical values, and the other six cells stayed equal;
- the 1003 probe of the flip-only control (16:19) finished the control's 45.03 mean.

**What this step was.** Physically, the +2.05 is an orientation choice on bp_fe, made from receipts of that same host. On run Y's host, inverting the official grouping on bp_fe/1001 and bp_fe/1002 cost −17.53 and −14.65. Don't assume the sign transfers across hosts.

### Decisions the Harness should learn from

1. **Account for gains per seed before accepting a net gain.** 34.39 hid +51.9 and −47.6 on the same design, and R2 in run X hid +38.26 against −11.31.
2. **An intermediate metric is not the objective.** Area error improved by 85% while the score fell 8.4.
3. **Labels identical to an already-measured candidate's give bit-identical timing on the same host.** That is what made both steps predictable.

**What a formal run can and cannot reuse.**
- Lesson 3 is not available to a formal Agent:
  - labels exist only after the evaluator trains, so a formal Agent cannot replay them in advance;
  - the development work also used saved embeddings, CPU replays, receipts from other days, single-cell probes and many more than 10 evaluations.
- Only general wording of lessons 1 and 2 may enter the first-request expert section.
- These must stay out of the Agent:
  - the 3-radius threshold;
  - the 75.4% condition;
  - the orientation choice;
  - the 41.73 code.

### What the two negative public-validation cells limit

The frozen 41.73 code scored on two validation cells; the other four were still pending:

| Cell | 41.73 code | Published start | 34.75 R4 on the 4090 |
|---|---:|---:|---:|
| swerv_wrapper/1001 | −29.38 | 8.39 | 6.59 |
| swerv_wrapper/1002 | −100 (raw −120.6) | −61.79 | −1.23 |

1. **Two cells from one design** give no validation mean, and nothing at all about bp_fe-asap7. That design is where the bp_fe-specific branch would matter.
2. **The published start comes from another host.** No same-host start exists for swerv, so "worse than start" cannot be split into code and host effects.
3. **Which branch each gate took on swerv is not recorded**, so the losses cannot be attributed to one gate.
4. **The −100 floor hides 20.6 points** of the raw −120.6.

So 41.73 shows that a developer, using information a formal run doesn't have, can optimise the nine training cells on one machine. It does not show generalization or a mechanism, and it should not be used to tune K1 or K1S. Here it serves only the development audit.

---

## 4. The minimal supervised K1 (K1S)

### What changed

The diff is `patches/K1-to-K1S.diff`, and it reproduces K1S exactly from the baseline. Three files change:

**`supervisor.py`** (new, 319 lines, no model calls, Python 3.8). After the second complete evaluation it builds a dossier (`supervisor.py:222`) from four sources:
- the logged requests (fields, null fields, expert flag, hashes);
- the logged replies;
- unified diffs of each evaluated program against its parent, with the docstring falsifiers quoted;
- the full nine-cell receipts.

It records three findings:
- inversion versus regrouping for each candidate;
- identical-label cells whose timing differs from the reference;
- the size of an added loss term, measured as `tp_gnn_final_loss` against a same-loss control.

It applies one rule (`review` at `supervisor.py:244`, `orientation_finding` at `:80`). If the step builds on a candidate that meets all of the following, that candidate is excluded as parent for the next step:
- most cells keep the official grouping or its exact inversion, within K1's existing `MARGINAL_FRACTION` of 0.1%;
- some of those cells are inverted;
- the candidate gained over its parent;
- the non-inverted cells did not gain.

The threshold is K1's own constant; nothing is tuned on these windows or on 41.73.

**`search_policy.py`** (+7 −4): `next_step(..., excluded=frozenset())` leaves excluded candidates out of incumbent, recombination and repair. `final_choice` is unchanged.

**`agent.py`** (+86 −8):
- Every model request and reply is logged as `model_request` / `model_response` events. Each distinct system prompt is stored once.
- `supervise()` (`agent.py:434`) sits between `next_step` and its use (`:520`).
- The note travels in that step's request only (`:619`).
- The submission carries `supervised_by` and `parent_source_sha256` (`:707`).
- After the next receipt, a `supervisor_check` is written (`:488–490`).

**Persistence, expiry and undo.**
- `supervisor_review` is written before the decision takes effect. On restart it is reloaded, so the review is not repeated and no evaluation is spent (tested).
- It applies while two evaluations are complete; after the third, K1's policy resumes.
- To undo: set `CHECKPOINTS = ()` in `supervisor.py`, or reverse the patch.

### Intervention record from run X's evidence

**1. Evidence the supervisor saw** (dossier `82626e6f…`).
- K1's default step: `refine_incumbent` on R2.
- R2's cells:
  - 3 identical to the start;
  - 4 inverted within 0.1%: bp ×3 and ariane/1003;
  - 2 inverted with 0.96% and 1.9% moved: bp_fe/1001 and bp_fe/1003.
- In summed cell points, the inverted cells give +38.26 and the rest −11.31. Net +26.95, which is +2.99 on the mean.
- R1's loss term: +0.155 to +0.158 against R2, which kept the official loss.

**2. Decision.** `exclude_parent`, rule `orientation_only_gain`, for the next step only. Final selection is unchanged.

**3. What changed in the actual round-3 request.** The parent changed from `203e2676…` (R2's decoder) to `official-initial`. The request fields:

| Field | K1 | K1S |
|---|---|---|
| `search_intent` | `refine` | `diversify` |
| `required_component` | null | `loss` |
| `decision.reason` | `refine_incumbent` | `supervisor_parent_excluded` |
| R2's receipt | in `parent_feedback` | in `incumbent_feedback` |
| `supervisor_note` | absent | added |

The system prompt and the other eight fields are byte-identical. Full table: `examples/round3-side-by-side.md`.

**4. How the next receipt tests it.**
- `supervisor_check` records:
  - adoption;
  - the cells whose grouping changed beyond an inversion;
  - inversions, score and the largest cell;
  - `withdraw` when most cells kept their grouping, meaning the redirect bought no attributable comparison.
- An illustration with run X's real round-3 candidate and receipt (also a loss edit of the start, written under X's Harness, so **not** K1S's counterfactual):
  - adopted, 9/9 regrouped, no inversions;
  - 23.39, carried by ariane/1002 at +89.94;
  - attributable, no withdrawal.
- At round 4, K1's rule returns (`combine_verified_gains`: R3's loss spliced into R2's decoder).

### No intervention needed: run Y's evidence

- K1's step is the shelved alternative, which builds on no candidate, so the decision is `keep`.
- Requests and the submitted source are identical in both arms.
- The dossier still records, for people only, bp's identical-label timing differences.

### Limits

- **The rule is narrow.** It would not have stopped Y's eight sub-0.3% rounds, which had no inversions.
- **With one checkpoint and one-step validity, the adjustment is a one-round detour.** K1 goes back to R2's decoder at round 4. Checkpoints at R2, R4, R6 and R8 cost nothing in model calls. Test them as a separate arm, because they change more than round 3.

---

## 5. Is the supervisor worth its cost? A controlled comparison

**Arms.**
- **K1 (control):** the delivered K1 plus `shared-K1-probe-fix.diff`.
- **K1S (treatment):** the same plus `K1-to-K1S.diff`.

**Held equal in both arms:**
- the official start and the loss-first opening;
- `deepseek-flash` at low effort;
- the 188-unit expert section, sent in the first generation request only. The tests check this from the logs: `expert_section` is true only on call 1.
- 10 official submissions and RMB 15 of model spend, with supervisor calls counted (K1S has none);
- the nine training cells.

**Excluded from both arms:** the 41.73 code and its thresholds, receipts from other runs, and public validation during the run.

**Hardware.**
- Pairs of machines with the same GPU model, preferably 3090s, which reproduce the published start.
- Run one K1 and one K1S at the same time, then swap machines for the next pair.
- Measure the official start once per machine outside the arms, so that "beats the start" is judged against the same host.

**Metrics, fixed before the first run.** Per run, from the receipts:

| Metric | Definition |
|---|---|
| First round that beats the start | First complete matrix above the same-host start. Also report the first round whose gain is not orientation-only |
| Duplicate candidates | (a) same function AST; (b) bit-identical labels on all nine cells as an earlier candidate; (c) the same grouping up to inversion on at least 8/9 cells |
| Best complete nine-cell score | Official score of the final choice |
| Weakest design | bp-ng45 case mean of the best candidate against the same-host start |
| Cost to the other two designs | bp_fe and ariane case means of that candidate against the start |
| Process | Model RMB, wall-clock, supervisor triggers, adoption, and the share of `supervisor_check` results that are attributable |
| Public validation | Of the final choice only, reported separately |

**How large an effect can be seen.**
- Best scores of historical runs vary by several points (for example 27.50, 29.67, 32.68 and 34.75). These come from different Harness versions and hosts, so they only indicate the spread.
- Paired detection of a 3-point effect, assuming a paired-difference SD near 4.5 points, needs on the order of 15–20 pairs, about 300–400 evaluations.
- A 2–4 pair pilot can detect only large effects or process differences.

**Recommended sequence.**
1. A free offline pre-screen: replay every archived R1/R2 window through both arms and count the windows where the round-3 decision differs.
2. A pilot of 3 crossover pairs. Read the decision-level metrics and the paired sign of the best score, and keep the uncertainty explicit.
3. Expand only if the pilot shows no harm.

**Withdraw the supervisor if:**
- it triggers and most `supervisor_check` results are `withdraw`;
- it loses an evaluation (a failed or invalid round 3);
- K1S's best is below K1's in every pilot pair.

**Cost.**
- Model spend: historical runs used 0.77–1.49 RMB of 15. K1S adds no calls.
- An LLM supervisor variant would add roughly 0.1–0.2 RMB per checkpoint, estimated from logged costs (a 13.6k-in / 6.0k-out call cost 0.067 RMB).
- **The real cost is the evaluation the supervisor redirects.** That makes it a result metric, not an overhead.

---

## 6. Tests actually run

Outputs are in `test-output/`.

| Suite | Python 3.8.20, no NumPy | Python 3.12.3 + NumPy 2.5.5 |
|---|---|---|
| `tests/test_supervisor.py` (17 tests: replays of both windows in both arms, restart, round-3 check and expiry, findings, expert-section count, probe defect, 3.8 syntax) | 15 pass, 2 skipped (NumPy-only probe tests) | 17 pass |
| K1's own 19 tests against K1S | 18 pass. 1 fails by design: K1's scope check requires `search_policy.py` to equal K0's | same |
| Legacy 22 search tests against K1S | 21 pass, 1 skipped (needs NumPy) | 22 pass |
| `patch -p1` of `K1-to-K1S.diff` onto `baseline-K1/` | reproduces `K1S/` byte for byte; the probe fix applies on top | — |
| Package `verify.py` and `SHA256SUMS.txt` | four means verified; 331/331 files match (one name is garbled by the zip's encoding, but its hash matches) | — |

**Not run:**
- the real model;
- the official bridge or validator;
- GPU training or physical evaluation.

Any effect of K1S on official scores is therefore **untested**.
