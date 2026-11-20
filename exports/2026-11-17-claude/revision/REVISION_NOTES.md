# Task 2 harness revision

Base: the Agent directory in `claude-harness-review-latest.zip`.
Apply `harness-revision.patch` with `patch -p1`, or copy `AgenticBench/agent/loss_decoder/` over the snapshot.

## Files

| File | Change |
| --- | --- |
| `agent.py` | Rewritten run loop. Decision rules moved out; proposal gates, retry, recombination and shelf added. |
| `search_policy.py` | New. Pure functions: evidence classes, mechanism families, next step, final selection. |
| `decoder_probe.py` | New. Runs a candidate decoder on synthetic inputs before submission. Skipped without NumPy. |
| `paired_feedback.py` | Adds `result_failure`; the log loader keeps retry, recombination and shelf lineage. |
| `prompt.md` | Describes the new request fields and decision reasons. The expert section is no longer than before (78 words, 537 characters; was 79 and 552). |
| `program.py`, `opening_review_prompt.md` | Unchanged. |

Only this directory belongs in the official task package. `tests/` and `experiments/` are development material.

## Next-hypothesis policy

`search_policy.next_step` reads every official reply of the run and returns the first rule that applies.

1. **Infrastructure failure on the latest submission.** Resubmit the same source once, if nothing was measured or its measured cells lead the reference.
2. **Contract failure on the latest submission.** Repair that candidate and that function once.
3. **Opening controls.** One decoder-only and one loss-only edit of the official start. The decoder goes first because it always reaches the assignment; `opening.txt` restores the other order.
4. **Opening alternatives.** Up to two proposals that the text review set aside are evaluated too, decoder edits first.
5. **Recombination.** When a loss-only and a decoder-only edit both beat the published start, their exact splice is evaluated. No model call.
6. **Inert or marginal result.** Diversify, and require the other function to change.
7. **Concentrated regression.** One targeted repair, as before.
8. **Nothing beats the published start.** Explore from the start, on the function with fewer effective tests.
9. **A verified incumbent leads.** Refine it once, then add mechanisms from other families on top of it.

## Official failure evidence

- Each reply is classed as `effective`, `marginal`, `inert`, `contract_failure`, `environment_failure` or `unverified`.
- `inert` means the same WNS and TNS as the parent on most cells, or an identical organizer-reported assignment.
- Infrastructure failures do not consume an opening slot and do not count as a failed hypothesis.
- A matrix is complete only if every scheduled cell has one finite official score, completed, and did not stop for an infrastructure reason. A verified physical failure keeps its floored score and counts.

## Gates before an evaluation is spent

- Exact repeat of an evaluated program.
- The same edit of the same function as an inert candidate, with coefficients changed by less than 10x.
- For `diversify`: a coefficient-only variant of any evaluated program, or a mechanism family already evaluated twice.
- For decoders, when NumPy is available: wrong label type or shape, top-die area outside 0.47 to 0.53, an exception, or labels identical to the parent's on six synthetic inputs.

After three rejections in one step the diversity gates are dropped and the other function is requested. After twelve the step stops asking the model.

## Final selection

The highest official score among candidates with a complete verified matrix; mean TNS improvement breaks ties; the earliest candidate wins an exact tie. No score is recomputed locally.

`RETURN_START_WHEN_UNBEATEN` in `agent.py` is off. When on, the Agent returns `context.baseline_candidate` if no complete candidate beats the published start. Turn it on only after the organizers confirm that ID is a valid final answer.

## Tests

```
python3 -m unittest discover -s tests -v
AGENT_DIR=/path/to/snapshot/AgenticBench/agent/loss_decoder python3 -m unittest tests.test_replay -v
REPLAY_TRACE=1 python3 -m unittest tests.test_replay      # prints the ten-evaluation trace
```

`tests/test_replay.py` runs `Agent.run` against a mocked bridge and a scripted model. The scripted world encodes one measured fact: the excess-weight pull at 1x and 4x left the assignment and timing identical. Everything else in that world is invented, so the tests show how evaluations are spent, not which algorithm is better.

## Proposed A/B

`experiments/candidates/criticality_weighted_positives.py` against `uniform_weighted_positives_control.py`. The control applies the same average multiplier to every positive pair, so the two differ only in which pairs carry the weight.
