# Task 2 harness review handoff

The goal is to improve an Agent that searches for better loss and decoder functions for 3D chip netlist partitioning. During a contest run the Agent uses the official model gateway. The official evaluator measures final physical timing with WNS and TNS. Codex runs the experiments and implements selected harness changes. Claude reviews the evidence between experiments and proposes the next controlled change.

The review archive includes `TASK_BRIEF.md` and `reference/` for the task and the published interface. `historical/` contains the November 16 exports: the recorded decisions from six early runs and the physical cell comparison. Those runs predate payload tracing. Their partial results are useful for locating failure stages and candidate changes. The artifact for the new 4090 comparison can be added after the run is collected.

## Collect one run

1. Save the exact Agent source, official task instructions, run configuration, reference version, and evaluator receipts with per-cell metrics. Give each run its own label and trace. When comparing harnesses, use matching baselines, cases, seeds, and budgets. Preserve physical failures and missing cells in the record.
2. Copy the run's `search.jsonl` from the Agent working directory. Generate a compact index with `python summarize_trace.py search.jsonl run-overview.json`. Open `run-overview.json` first. Use call IDs in `search.jsonl` to inspect the input sent to the model, its visible reply, and the surrounding Agent decisions. Use evaluation request IDs to match exact source, evaluator feedback, and retries. Review the trace and logs for credentials or private details before sharing.
3. For an older run without `model_request` events, the index reports `actual_model_input_recorded: false`. Candidate code and evaluator receipts from that run can still be reviewed. Model input and output need their own recorded evidence.

## Review request for Claude

> Review `run-overview.json` first, then inspect the matching records in `search.jsonl`, the Agent source, and the official rules. Reconstruct what information was available to the Agent at each decision and what it actually passed to the contest model. Use the recorded replies and evaluator receipts to identify where the search stalled, discarded a valid proposal, revisited the same mechanism, or spent a slot without gaining new evidence. Cite call IDs or evaluation request IDs. Treat incomplete matrices and infrastructure failures as such. Recommend at most two concrete harness changes. For each change, provide the exact file or function to edit, the expected effect on search decisions or WNS/TNS, and the smallest official A/B experiment that could falsify it. Separate observations from hypotheses and flag any rule questions.

## Changes in this copy

- The trace records the exact payload sent by the Agent to the model gateway, the reply's visible text and available token counts, policy decisions, exact submitted source, and available evaluator feedback. It does not record gateway headers or hidden reasoning.
- The local decoder probe still blocks invalid shapes, non-integer or non-binary labels, and empty dies. Raw area imbalance and equality to the parent's labels on synthetic inputs are logged as diagnostics. The official flow applies its protected area repair.
- The repeated offline observation in the main prompt was removed. The declared expert-knowledge section remains the place for that observation.
- Search scheduling and retry policy come from the saved Claude revision. This copy requires a real bridge smoke test before using its scores to judge improvements.
