# Rolling ablation for the branching Harness: audit, patch and verification

**Status**

| Item | State |
|---|---|
| Patched Agent, diff against an identified base, ZIP | Done (§1) |
| End-to-end `Agent.run()` verification (12 scenarios, Python 3.12.3 and CPython 3.8.20) | Done (§2) |
| The team's own unit tests (`next-harness/tests/`) | **Pending.** The auto-mode classifier blocked running them here; commands are in §7. |
| Integration with `harness-ablation` | **Pending.** That source is not in any archive I received; §1.3 is written against the three features you named. |
| Tolerance and noise analysis, replay under alternative thresholds | Done (§3) |
| Dossiers for each changed decision, generation fields, intervention checks | Done (§4) |
| Live, budget-matched GPU comparison | Specified only (§5). Nothing here ran on a GPU. |

**How to read the evidence.** Replay results are decisions on archived prefixes. The physical outcome of any changed decision is unknown, and no score below comes from a new GPU run.

## 1. Base, patch and what it adds

### 1.1 Base and patch

- **Base.** `sources/branching/` from `claude-rolling-ablation-and-self-test-audit-en.zip`; hashes for all 11 files are in `BASE.json`.
  - `agent.py` and `prompt.md` match the bundle's `review_sha256`. They are the English review translations; your untranslated originals hash to `7e517d87…` and `d8ed3f95…`.
  - The `agent.py` hunks change code and should apply to the original with little fuzz. The `prompt.md` hunk is English text and needs a manual edit on an untranslated prompt.
- **Patch.** `patches/4-rolling-ablation.patch`. `patch -p1` on the base reproduces `next-harness/` exactly.

| File | Lines |
|---|---|
| `agent.py` | +194/−29 (wiring only) |
| `paired_feedback.py` | +21/−1 |
| `prompt.md` | +4/−2 (expert section unchanged, 106 words) |
| `ledger.py` (new) | 689 |
| `rolling_plan.py` (new) | 774 |
| `self_test.py` (new) | 369 |

- **Unchanged:** `search_control.py`, `decision_evidence.py`, `candidate_reply.py`, `program.py` and the team's tests.
- **ZIP:** `/root/code/claude-rolling-ablation-review.zip` holds the tree, the pristine base, the patch, tests, fixtures, tools and examples.

### 1.2 What already exists and what the patch adds

The `harness-ablation` column restates your description; I have not seen that code.

| Capability | branching (base, read in full) | This patch (tested) | harness-ablation |
|---|---|---|---|
| High-effort planning | None: every call uses `effort: low`, opening review included | One high-effort call at hard branches (duplicate, stall, contradicted plan, protected regression, antagonistic merge). At least two offered options, JSON reply checked, at most 4 per run, cached per round. | Yes |
| Ablation against the measured parent | Paired parent comparison in feedback; `targeted_repair`; no scheduled ablations | Parent contrasts are reused as controls. Removals relative to the start for a champion that changed both functions. Transplants and merges. All are code-assembled splices, no model call. | Yes |
| Predeclared protection | `targeted_repair` names `protect_gain` and `repair_regression`; nothing checks them afterwards | A contract on every edit (target, protected designs, plan-time tolerances), judged after the nine cells; verdicts trigger planning | Yes |
| Controls found anywhere in the run | No (parent, plus one `related_experiment`) | Exact one-function contrasts, 2×2 squares, missing counterparts (`ledger.py`) | Unknown |
| Die-exchange and duplicate handling | Timing twins; flip-adjusted change against the parent | Per-cell relation (identical, exchange, local, regroup); label fingerprints; duplicates verified by labels or by timing only | Unknown |
| Sensitivity-aware decisions | No | Per-design sensitivity from this run; a repair is declined when its protected gain is inside it | Unknown |
| Preflight before a slot is spent | Official validator; inert-mechanism rejection | Python 3.8 syntax, byte limit, manifest, edit footprint, identity rules, contract probes | Unknown |
| Compact generation request | No | One `experiment` block; repeated views dropped; floats cut to 6 significant digits | Unknown |
| Persist first, survive errors | `feedback_degraded` for summaries | `official_receipt` written before enrichment; the `Agent.run` guard returns the best measured candidate | Unknown |
| Final selection | Highest official complete training score | Unchanged | Presumably the same |

### 1.3 Integration with harness-ablation (pending its source)

**Interface.** The new modules are standard library only and are called through three functions:
- `ledger.build_ledger(summaries, sources, schedule, start, initial_source, fingerprints)`;
- `rolling_plan.plan_next(ledger, baseline, remaining, total, considered, planning_calls)`;
- `self_test.static_checks` and `self_test.run_probes`.

`baseline` is whatever the host Harness would do next: (parent candidate ID, intent, decision dict). So harness-ablation can keep its own scheduler and use these modules as an advisor.

**Conflicts and how to resolve them:**

| Seam | Conflict | Resolution |
|---|---|---|
| Parent selection | This patch overrides the baseline parent in two cases: a removal follow-up and a declined repair (`plan["decision_override"]`). harness-ablation's planner also chooses parents. | One authority: harness-ablation keeps it. Pass its choice as `baseline` and apply the overrides only as offered options, or disable them (`_declined_repair` needs its decision to expose a `protect_gain`-like field). |
| Ablation scheduling | Both systems could schedule the same control. Measured-parent ablations and these removals (relative to the start) answer different questions. | One shared list of considered programs (`ledger.factor_pair` over every proposed program). One combined cap of ⌊budget/3⌋ for all ablations and splices. No two in a row. No ablation without a later slot to act on it. |
| High-effort planning | Two planners would double cost and disagree. | Keep harness-ablation's planner and set `rolling_plan.MAX_PLANNING_CALLS = 0`. Feed it this patch's `options`, `lessons` and contracts as extra evidence. |
| Protection checks | Two predeclared checks with different tolerances. | Keep one check, with tolerances fixed when the plan is made. If harness-ablation uses fixed or zero tolerances, consider the calibrated table, keeping §3's caveats in view. |
| Final selection | None expected: both select by official training score. | Keep harness-ablation's rule. Add the error guard only if it has none. |
| Search log | Event names `plan` and `submitted`, and attempt fields such as `experiment`, may collide. | Rename or nest on integration. `load_attempts` must keep the `experiment` field for restarts. |

**Still needed:** the harness-ablation source. With it I can write the concrete diff, resolve the table above in code, and port the 12 end-to-end scenarios. The fixtures and stubs in `tests/` are Harness-independent, and only the expected event names would change.

## 2. End-to-end verification of the patched Agent.run()

**Setup.** `tests/test_agent_integration.py` runs the team's `agent.py`, `search_control.py`, `paired_feedback.py` and `candidate_reply.py` together with the new modules, through the offline bridge stand-in `tests/stubs.py`. Each test restarts the Agent after k real archived rounds: official cells, organizer partition diagnostics, accepted sources and lineage. Model replies are scripted.

**Result.** All 12 pass on Python 3.12.3 (NumPy 2.5.5, PyTorch 2.15 CPU) and on CPython 3.8.20 (neither installed).

| Scenario | What the test asserts |
|---|---|
| **A missing control, assembled and submitted exactly once** (`test_missing_control_is_assembled_and_submitted_exactly_once`) | Restart after original round 4. Round 5 is the removal splice (start loss, R4's decoder) with no model call. Its request ID appears once in the bridge history. Its `official_receipt` precedes `evaluated`. Round 6 is the follow-up its outcome selected: a loss edit of the removal program, reason `removal_follow_up`. |
| **An old control, found after a restart and reused** (`test_an_old_control_is_found_after_a_restart_and_reused`) | Restart after rounds 1–4 plus the removal as an earlier process recorded it. The removal is not resubmitted. The request carries its conclusion ("R4 needs its loss change") and the comparison `R4-R5`. |
| **A failed preflight that spends no slot** (`test_failed_preflight_spends_no_evaluation_slot`) | A decoder with `if seed == 1002` is rejected (`identity_rules`). The next generation gets the diagnostic, and the bridge history grows by exactly one evaluation. |
| **An optional feedback failure after a valid score** (`test_optional_feedback_failure_after_a_valid_score_keeps_the_score_and_the_best`) | The analysis of a new best receipt raises the archived crash (`'int' object has no attribute 'bit_count'`). The order of events is `official_receipt`, then `incumbent`, then `feedback_degraded`. `program.py` holds the new best, `Agent.run` returns it, and there is no `agent_error`. |
| Label fingerprints unreadable | `feedback_degraded`; the removal and its follow-up still run |
| No removal when no slot is left to act on it | With one slot left the plan is an edit |
| Declined repairs after rounds 7 and 9 | The generation request has parent R4, intent `decoder_only`, reason `extend_best` with the sensitivity note, and no repair fields |
| Contract in the request | Target bp_fe; protect bp and ariane133; two hypotheses; `decision_evidence` dropped; 9 cells in `last_trial`; under 20,000 characters |
| Planner failure | `plan_degraded`; the request has no `experiment`; the branching decision is submitted |
| Hard branch after round 6 | One high-effort call with options X1 and X2, then one low-effort generation. Its `experiment_plan` and `expect_footprint` arrive, and `intervention_shape` passes. |
| Unexpected error | `agent_error`; the best measured candidate is returned |

**Bugs found only end to end, and fixed:**
- Removal contracts have no target design (measurements), but the splice record still read `contract["target"]["case"]`. That call sat outside the splice path's error handling, so the `TypeError` reached `Agent.run`'s guard. The guard returned the best candidate as designed, but the round was lost.
- Fixes: `splice_hypothesis` no longer assumes a target, the call now runs inside the guarded block, and `test_a_removal_splice_record_needs_no_target` covers it.

### 2.1 Which probes run in the contest image

| Probe | Needs | Contest Agent container | Evidence |
|---|---|---|---|
| Static checks | Standard library | Run | — |
| Decoder contract | NumPy | **Run for custom decoders.** Skipped for decoders that call `reference_global_two_way` unless a supported provider is configured; none is. | The archived formal run logged a rejection only the old NumPy probe could produce ("The decoder raised KeyError on a synthetic probe with read-only inputs: '__import__'"), under `/usr/lib/python3.8`. 8 of 10 decoders in that run were custom. |
| Loss contract | PyTorch | **Unknown.** Skipped with a logged reason if absent. | No archive shows PyTorch in the Agent container. |
| Planner paper probes | Whatever the above provide | Advisory only | — |

The Agent now writes a `runtime_capabilities` event at startup, so the first live round answers the PyTorch question.

**Helper.** The Agent no longer ships a copy of the official decoder helper. `self_test.HELPER_PROVIDERS` is empty, and helper-calling decoders are reported as skipped. The test double lives in `tests/probe_helper.py`, outside the Agent.

**The `__import__` rejection explained.** CPython's `PyImport_Import` looks up `__import__` in the builtins of the calling frame's globals, and NumPy imports lazily from C. Candidate code run with a restricted `__builtins__` table can therefore fail inside NumPy. Probes now run validated programs with the interpreter's normal builtins, as the evaluator does. `ImportError`, `NameError`, `MemoryError` and `RecursionError` count as probe-environment problems and never block a submission.

## 3. Tolerance and noise: repeatability versus sensitivity

Raw data: `examples/noise_audit.json`; replay: `examples/threshold_replay.json`. Both are regenerated by `tools/noise_audit.py`.

**Repeatability (matched repeats).** Identical labels measured twice gave identical score, WNS and TNS in **all 15 pairs**: 6 within a server and 9 across servers. The pairs are bp/1002 (10), bp_fe/1002 (3), bp_fe/1003 (1) and ariane/1002 (1, across servers). Every repeat is of start labels. The only whole-matrix repeat of a candidate, R6 against R4, is equal on timing alone, with no label proof. There is no measurement noise to calibrate. **All tolerances in this patch are sensitivity heuristics**, and the code says so.

**Sensitivity (raw observations).** A pair is two programs measured on this host whose labels on a cell are each within 10% of one grouping, with the same die orientation, and whose timing differs. The archive has no label files, so the distance between the two programs is bounded but not known. Pairs share programs (n programs give up to n(n−1)/2 pairs per cell), so they are not independent.

| Prefix | bp_fe pairs, median | bp pairs, median | ariane133 pairs, median | Official-score tolerance |
|---|---|---|---|---|
| Original R1–R4 | 8, 6.48 | 6, 1.97 | 15, 57.88 | 11.23 |
| Original R1–R7 | 34, 7.70 | 31, 3.52 | 46, 28.94 | 5.80 |
| Original R1–R9 | 67, 6.80 | 67, 4.90 | 76, 21.08 | 4.37 |
| **Original R1–R10** | **76, 7.25** | **74, 4.90** | **80, 26.93** | **5.45** |
| Evidence run R1–R3 | 8, 7.46 | 9, 1.03 | 7, 36.38 | 7.18 |
| Panel R1–R3 (one seed) | 0 (default) | 0 (default) | 5, 87.62 | 29.30 |

**Derivation of ±5.4 (original run, all 10 rounds).**
- Cell sensitivity s is the median |Δscore| over the pairs.
- The tolerance for a case mean is max(2, s/√3), giving 4.185, 2.830 and 15.547.
- The official score is a mean of three case means, so its tolerance is √(4.185² + 2.830² + 15.547²)/3 = 5.449.
- The √3 and the root-sum-square assume independent seeds and cases. That is a heuristic, not a fitted error model.

**Replay of rounds 4, 7 and 9 under alternative thresholds:**

| Setting | After R4 | After R7 | After R9 |
|---|---|---|---|
| Default (median, ×1, local 0.10, ÷√seeds) | removal | repair declined | repair declined |
| 25th percentile | removal | repair kept | repair kept |
| 75th percentile | removal | declined | declined |
| Half the median | removal | declined | **kept** |
| Twice the median | removal | declined | declined |
| Local pairs within 0.05 | removal | declined | **kept** |
| Local pairs within 0.20 | removal | declined | declined |
| No ÷√seeds | removal | declined | declined |
| Default tolerance 2 or 10 | removal | declined | declined |
| Zero tolerance (every decrease counts) | **transplant** (R4 loss) | kept | kept |

- **R4's removal** is a structural decision: the champion changed both functions and one counterpart is missing. Only zero tolerance changes it, because that makes every small case gain "supported" and a transplant outranks the removal.
- **R7's decline** (protected +13.16 against a ±28.94 median) holds in 9 of 11 settings.
- **R9's decline** (+15.12 against ±21.08) holds in 7 of 11 and is the threshold-sensitive one.
- No setting changes any decision on the evidence-driven run.
- **Caveat:** early in a run the official-score tolerance is wide: 11.23 after round 4, from 15 ariane133 pairs. So a removal must lose more than 11 points before the plan concludes the change was needed.

## 4. What deeper reasoning buys

**Where the high-effort planner runs.** The three changed decisions are made from ledger facts, with **no model call**. By default the high-effort planner runs only at the duplicate and stall branches (original rounds 6, 8 and 10).

With `rolling_plan.PLAN_ON_OVERRIDE = True`, each changed decision also asks the planner. The planner is offered the rolling choice and the branching choice, about 4.6–4.9k characters per request.

**What that buys is unmeasured.** It cannot see anything the ledger has not already computed. At most it re-chooses between two offered options, and writes the edit brief and the expected footprint for the follow-up generation. Measuring its value takes an arm with the switch on (§5).

Full dossiers, with the exact planner request and the captured generation request, are in `examples/dossiers.json` and `examples/requests/`.

| | After original R4 | After original R7 | After original R9 |
|---|---|---|---|
| Branching chose | Extend R4, loss | `targeted_repair` of R7 (protect ariane/1003 +13.16, repair ariane/1001 −141.96) | `targeted_repair` of R9 (protect ariane/1002 +15.12, repair ariane/1001 −64.65) |
| Evidence the plan uses | R4−R2 = +5.33, 89% from exchanged dies. R4 changed both functions from the start. The counterpart (start loss, R4's decoder) is unmeasured. 6 slots left. | ariane133 cell sensitivity 28.94 (46 pairs). R4's ariane/1001 value came from exchanged dies. | Sensitivity 21.08 (76 pairs). Same exchanged R4 cell. |
| H1 | R4's loss change still contributes once its decoder is in place | The protected gain is real and the loss is repairable | Same |
| H2 | R4's score is carried by its decoder; the loss change adds nothing measurable | The protected gain is within sensitivity, so there is nothing measured to keep. The −141.96 is real, but R4's value there was an exchange. | Same, with ±21.08 and −64.65 |
| Experiment | The removal splice, one slot, no model call | A decoder edit of R4. It does not test H1; the repair itself is H1's test. | Same |
| Gains to protect | None (a measurement). The follow-up edit protects ariane133 (±16.54). | ariane133 mean within 16.71 of R4 | ariane133 mean within 12.17 of R4 |
| Falsifier | H1 fails if the removal scores within 11.23 of R4. H2 fails if it scores more than 11.23 below. | bp does not improve on most seeds against R4, or ariane133 falls more than 16.71 below R4 | Same, with 12.17 |
| Generation request sent | None for the removal. The follow-up (round 6 in the replay) totals 20,285 characters. | 23,439 characters | 23,798 characters |

**Fields passed to code generation**, character counts for R7. The intent is `decoder_only`, parent R4, and every float in model-facing JSON is cut to 6 significant digits.

| Field | Characters |
|---|---|
| `decision` (reason `extend_best`, plus the sensitivity note) | 1,486 |
| `parent_program` | 4,132 |
| `training_cells` | 363 |
| `parent_feedback` | 893 |
| `last_trial` (compacted) | 7,258 |
| `prior_trials` | 2,300 |
| `related_experiment` | 931 |
| `experiment` | 5,722 |

The `experiment` block carries:
- `experiment`: the question, the two hypotheses and the falsifier;
- `contract`: target bp, protect ariane133 with plan-time tolerances;
- `anchor_review`: nine paired rows against the start, with `start_measured_on`;
- `comparisons`: up to three exact contrasts;
- `lessons`.

Not passed: `decision_evidence` and `earlier_edits_from_selected_parent` (their facts are in `experiment`), and the full receipt comparison against the start.

**How the Harness checks that the generated diff implements the intended intervention.** The checks below are recorded in every `submitted` event's `preflight` field.

| Check | Verifies |
|---|---|
| `manifest` | Exactly the declared function changed, relative to the planned parent. For a splice, both functions are byte-for-byte the declared measured donors (exact factor IDs). |
| `intervention_shape` | When the plan sets `expect_footprint`, the change is the declared kind: `structural`, or `coefficients_only` (a dose change). |
| Branching's checks | `proposal_keys` (the unchanged function is identical), the docstring hypothesis fields, and `repeated_inert_mechanism` |
| `identity_rules` | No branch on `seed`, no training seed values, no design names |
| Probes | Legal labels and a finite, connected loss. The change relative to the parent on the fixture is advisory. |

What code cannot verify is the semantic claim ("ranks boundary groups by margin"). That is tested only by the nine-cell result against the contract.

## 5. Fair live comparison

**Arms:**
- **A:** harness-ablation as is.
- **B:** branching plus this patch (`next-harness/`).
- **Optional B′:** B with `PLAN_ON_OVERRIDE = True`, to price deeper reasoning at the changed decisions.
- **Later C:** harness-ablation with these modules once integrated (the adoption question).

**Held equal:**
- the image (`sha256:f2401e97…`, the formal-run image) and the GPU type (RTX 4090, 49,140 MiB, as in the archived host record);
- the official model and gateway (DeepSeek-V4.1-Flash, CNY 15);
- the official start, the grid (3 training designs × 3 seeds) and 10 evaluations;
- the bridge version and retention settings;
- no development edits during a run.

**Schedule:**
- Run A and B at the same time on two fleet servers. Identical labels gave identical timing on every server pair archived (§3).
- For a second replicate, swap servers. Two replicates per arm is about 2 × 19–20 hours on two servers.
- With n = 2, report every run and the per-arm mean, and claim no significance.

**Metrics per run, from search logs and receipts:**

| Metric | Definition |
|---|---|
| Best measured score | Highest official complete training score, and the slot where it was first reached; best-so-far by accepted slot |
| Selected score | Official training score of the candidate `Agent.run` returned. Reported separately even if equal. |
| Public validation of the selected candidate | 6 public cells, after the run; development evidence only, never fed back |
| Useful ablations | Control evaluations (B: removal, transplant, merge; A: its measured-parent ablations) whose outcome selected the next parent or function under the table declared before submission, or that became the champion |
| Duplicate outcomes | Evaluations repeating an earlier one on all cells, verified by labels; timing-only matches reported separately |
| Rejected candidates | Validator rejections, preflight rejections and splice rejections (no slot spent), counted separately from evaluated candidates with contract failures (slot spent) |
| Model cost | Input and output tokens per call (from `model_response` usage) priced by the official table, split into planning and generation; number of high-effort calls |
| Wall time | First submission accepted to last receipt; per-evaluation duration; Agent time between a receipt and the next submission |
| Robustness | `agent_error`, `plan_degraded`, `feedback_degraded`, `generation_stop` |

**Pre-registered criteria for adopting B or C:**
- no `agent_error`;
- no evaluated candidate the preflight should have rejected;
- every splice's follow-up matches its decision table;
- fewer slots lost to duplicates and invalid programs than A;
- a selected score not lower than A's by more than the official-score sensitivity at the end of the run (about 5 points on the archived run).

Replay findings (§3, §4) are reported in a separate section and never pooled with these measurements.

## 6. Failure modes

1. **ariane133 dominates the score.** Protection on it is weak, and a contract can hold while the official score falls. The verdict lists every protected cell that regressed; the official score still selects.
2. **Early-run sensitivity is wide.** It was 11.23 after round 4, and the removal follow-up is permissive until more pairs accumulate.
3. **R9's decline depends on the threshold** (§3). R7's mostly does not.
4. **Label files unreadable.** The fallback relations, bounded by changed fractions against the start, are approximate, and duplicates become `timing_only`. The archived crash shows the files are readable in the contest container.
5. **Published start cells (host drift).** These produce `mixed_reference` designations.
6. **Splices pair functions designed for other contexts.** This is the question being measured. An antagonistic result keeps the stronger single change.
7. **The planner returns unusable JSON.** The deterministic option stands. High-effort calls are capped at 4.
8. **Probes and the reference helper.** No supported helper means decoders that call it are not probed: 7 of the 17 archived programs (2 in the original run, 2 on the panel, 3 in the evidence run). PyTorch may be absent.
9. **Identity-check false positives.** A legitimate comparison involving `seed` is rejected and regenerated.
10. **Preflight rejections end the search early.** They count toward branching's stop after 5 consecutive invalid proposals.
11. **The base is a translation.** The `prompt.md` hunk needs manual application to the untranslated prompt (§1.1).
12. **harness-ablation conflicts** (§1.3) are unresolved until its source is reviewed.

## 7. Commands

From the review root:

```
# 40 unit and replay tests (3 need NumPy and are skipped without it)
python3 -I -B -m unittest discover -s tests -p "test_rolling.py" -v
# 12 end-to-end Agent.run() scenarios; DUMP_REQUESTS saves every model request and the key log events
DUMP_REQUESTS=/tmp/requests python3 -I -B -m unittest discover -s tests -p "test_agent_integration.py" -v
# the team's own tests, pending here (needs permission to run the team's test files)
cd next-harness && python3 -B -m unittest tests.test_search_control tests.test_decision_evidence tests.test_assignment_compat
# examples, noise audit and dossiers
python3 -I -B tools/make_examples.py
python3 -I -B tools/noise_audit.py
python3 -I -B tools/make_dossiers.py /tmp/requests
```

Run the first two lines inside the image the Agent uses. They need no GPU, and the `runtime_capabilities` event shows which probes run there.

`test_second_candidate.py` also needs the official framework at `../official/contest-source/AgenticBench`, relative to `next-harness/`.

## 8. Files

- **Harness:** `next-harness/` (patched), `original/branching/` (pristine base), `BASE.json`, `patches/4-rolling-ablation.patch`.
- **Tests:**
  - `tests/test_rolling.py` and `tests/test_agent_integration.py`;
  - `tests/replay.py`, `tests/stubs.py` and `tests/probe_helper.py`, plus `tests/build_local_factorial.py`;
  - fixtures: `three_servers.json`, `branching_replay.json`, `local_factorial.json` and `ours_new_round4_request.json`.
- **Examples:**
  - `examples/decisions.json`, the replay of every prefix;
  - `noise_audit.json`, `threshold_replay.json` and `dossiers.json`;
  - `planner_after_claude_round_6.json` and `generation_after_evidence_round_3.json`;
  - `requests/`, the captured model requests and key log events.
- **Tools:** `tools/py38_gate.py`, `make_examples.py`, `noise_audit.py` and `make_dossiers.py`.

All development material stays outside the Agent directory.
