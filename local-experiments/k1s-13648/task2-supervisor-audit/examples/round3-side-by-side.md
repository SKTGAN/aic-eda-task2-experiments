# Round 3 before and after the supervisor

Both Agents received the same rounds 1–2 of run X (22120-independent), replayed from the recorded candidates and official nine-cell receipts. Columns: **K1** = the delivered K1, unchanged; **K1S** = K1 plus the supervisor in `patches/K1-to-K1S.diff`.

## Same evidence in rounds 1–2

| Call | K1 request sha256 | K1S request sha256 |
|---|---|---|
| call-01-generation.json | `7e2aa9404ce1c886…` | `7e2aa9404ce1c886…` |
| call-02-opening_alternative.json | `19820e1bc158cacb…` | `19820e1bc158cacb…` |
| call-03-opening_review.json | `def1bd5338ece34b…` | `def1bd5338ece34b…` |
| call-04-generation.json | `1ee487d7f2dbc983…` | `1ee487d7f2dbc983…` |
| call-05-opening_alternative.json | `d9e7b43224044fcc…` | `d9e7b43224044fcc…` |
| call-06-opening_review.json | `b8a8d08be4f6cee5…` | `b8a8d08be4f6cee5…` |

The round-3 system prompt is byte-identical in both arms.

## What each Agent sends as the round-3 request

| Field | K1 | K1S | |
|---|---|---|---|
| `avoid_mechanism_families` | [] | [] | same |
| `decision` | reason=refine_incumbent, candidate_id=203e2676d95a… | reason=supervisor_parent_excluded, excluded_candidate_id=203e2676d95a… | **changed** |
| `evaluations_remaining` | 8 | 8 | same |
| `incumbent_feedback` | null | receipt summary of 203e2676d95a… (score 23.42, 9 cells) | **changed** |
| `mechanism_ledger` | ebbb7303… loss[graph_scores+graph_weights] inert; 203e2676… decoder[custom+argmax+argsort+cumsum+sum+where] effective | ebbb7303… loss[graph_scores+graph_weights] inert; 203e2676… decoder[custom+argmax+argsort+cumsum+sum+where] effective | same |
| `parent_feedback` | receipt summary of 203e2676d95a… (score 23.42, 9 cells) | null | **changed** |
| `parent_id` | "203e2676d95aed3bcb076441c9947a07c3e70bbe0c0cad0a8e6f0d4ca51c7b1b" | "official-initial" | **changed** |
| `parent_program` | 3671 characters, sha256 73f0456079ad… | 846 characters, sha256 8f87b6dadc19… | **changed** |
| `previous_generation_issue` | null | null | same |
| `published_start_score` | 20.425060316261952 | 20.425060316261952 | same |
| `recent_feedback` | ebbb7303ecab… (5.47) | ebbb7303ecab… (5.47) | same |
| `related_experiment` | ebbb7303ecab… | ebbb7303ecab… | same |
| `required_component` | null | "loss" | **changed** |
| `search_intent` | "refine" | "diversify" | **changed** |
| `supervisor_note` | absent | see the full text below (1308 characters) | **changed** |
| `training_cells` | 9 cells | 9 cells | same |

### Full `supervisor_note` (K1S only)

> Cross-round review after 2 official evaluations of this run (this run's receipts only). Candidate 203e2676d95aed3bcb076441c9947a07c3e70bbe0c0cad0a8e6f0d4ca51c7b1b (official score 23.42, +2.99 against its parent) is not the parent for this step; it stays eligible for final selection. On 7 of 9 cells its final labels equal the official initial assignment or its exact inversion within 0.1% of instances (partition_assignment_changed_fraction). The 4 inverted cells (bp-ng45/1001, bp-ng45/1002, bp-ng45/1003, ariane133-ng45/1003) account for +38.26 summed cell points against its parent and the other 5 cells for -11.31. Its largest cell is ariane133-ng45/1003 at +44.81. Its gain therefore comes from inverting the initial assignment on those cells, not from a different grouping. Loss edit ebbb7303ecab06df43dc1de37f8dcc733d4ae6837e1e12df2f7a4f6de5cabfe9 raised tp_gnn_final_loss by 0.155 to 0.158 on every cell against 203e2676d95aed3bcb076441c9947a07c3e70bbe0c0cad0a8e6f0d4ca51c7b1b, which kept that loss unchanged (0.36% to 0.39% of the loss); 6 of 9 of its assignments were identical to the official initial assignment. In the docstring of each function you change, predict the share of instances whose die changes relative to the official initial assignment once a whole-assignment inversion is undone.

## The intervention record

**1. Evidence the supervisor saw** (dossier sha256 `82626e6f4ac7e1b6…`). It read the six logged requests and replies, the two parent→child diffs and both nine-cell receipts. The policy's default step was `refine_incumbent` on `203e2676d95a…`. That candidate's cells:

| Cell | Changed fraction vs initial | Inverted | Moved after undoing inversion | Δ vs parent |
|---|---:|---|---:|---:|
| bp_fe-ng45/1001 | 0.99041 | yes | 0.00959 | -10.36 |
| bp_fe-ng45/1002 | 0.00000 | no | 0.00000 | +0.00 |
| bp_fe-ng45/1003 | 0.98108 | yes | 0.01892 | -0.95 |
| bp-ng45/1001 | 0.99999 | yes | 0.00001 | +10.60 |
| bp-ng45/1002 | 0.99999 | yes | 0.00001 | -21.98 |
| bp-ng45/1003 | 0.99999 | yes | 0.00001 | +4.83 |
| ariane133-ng45/1001 | 0.00000 | no | 0.00000 | +0.00 |
| ariane133-ng45/1002 | 0.00000 | no | 0.00000 | +0.00 |
| ariane133-ng45/1003 | 0.99998 | yes | 0.00002 | +44.81 |

In summed cell points, the inverted same-grouping cells give +38.26 and the other cells -11.31, a net of +26.95; that is +2.99 on the official nine-cell mean.

**2. Decision.** `exclude_parent` under rule `orientation_only_gain`. Scope: the next step only; final selection unchanged.

**3. What changed in the actual round-3 request.**
- The parent is now `official-initial` (the official start, sha256 `8f87b6dadc19…`) instead of `203e2676d95a…`.
- The intent is `diversify` with a required `loss` change instead of `refine`.
- The request carries the new `supervisor_note` quoted above. Everything else is K1's own policy output.

**4. How the next receipt tests it.**
- The `supervisor_check` event is written after the next complete evaluation. It records:
  - adoption: the parent differs from the excluded candidate;
  - the number of cells whose grouping changed beyond an inversion;
  - inversions, score and largest cell;
  - `withdraw` when most cells kept their grouping.
- Replayed with run X's real round-3 candidate and receipt (also a loss edit of the official start; it was written under X's own Harness, so this illustrates the check and is not K1S's counterfactual score):
  - adopted = True; new grouping on 9/9 cells; inversions 0;
  - official score 23.39 (+2.96 vs parent); largest cell ariane133-ng45/1002 +89.94;
  - attributable = True; withdraw = False.
- **Expiry.** The adjustment covers one step. At round 4, K1's own rule returned: `combine_verified_gains` with parent `203e2676d95a…`.

## Run Y (10820-branching): no intervention

This replay uses Y's own decoder-first order (`opening.txt = decoder_only`) and its recorded opening alternatives. These files were produced on Python 3.8, where the decoder probe is skipped. With NumPy, both arms need `patches/shared-K1-probe-fix.diff` first (see the KnownDefect tests).
- Supervisor decision: `keep`.
- Both arms then submit the same shelved opening alternative, with no model call: source sha256 `76b9edc9f727…` (K1) and `76b9edc9f727…` (K1S).
- The review still logs, for people only, that bp-ng45 kept the start labels yet timed differently from the published start: bp-ng45/1001, bp-ng45/1002, bp-ng45/1003.

