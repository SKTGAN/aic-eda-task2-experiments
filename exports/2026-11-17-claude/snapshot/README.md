# Task 2 harness review bundle

Start with TASK_BRIEF.md and REVIEW_REQUEST.md. The requested outcome is an improved, executable harness.

- AgenticBench/agent/loss_decoder contains the opening-review harness, the most developed local version available for this snapshot. It uses matched parent-child feedback, failure evidence, retrieval of related experiments, opening hypothesis review, and a branch switch when timing is mostly unchanged. Its scoring advantage over the other harness versions remains unverified. Candidate generation, opening alternatives, and opening review use English prompts. The opening controller can compare two mechanisms before sending one to physical evaluation. It records organizer-reported assignment changes when they are available.
- reference contains the official initial two-function program, numerical interface, bridge API, read-only excerpts of the official area-balanced decoder and rounding, and published training measurements. The original rulebook is linked in TASK_BRIEF.md. The official runtime is required for real candidate evaluations.
- experiments contains English tabular data, sanitized per-run comparisons, and local candidate code. Only the Agent directory belongs under the official task package's Agent directory. The remaining files provide development and review context.

## Latest experiment

All four rows in experiments/latest_results.csv use bp_fe-ng45 / 1003, the same official image, and a 6 GiB local diagnostic container limit on an RTX 4060. The official starting program scored 55.91. The earlier all-edge timing affinity at 4x scored 43.09. The excess-weight variant scored 55.91 at both 1x and 4x. Both new runs measured WNS of -0.664914 ns and TNS of -173.788540 ns.

Every loss variant changed the bytes of the embeddings. The excess-weight 4x variant changed the raw clustering assignment of ten instances, yet the official decoder assigned all instances exactly as in the baseline. The new variants left the same 3,102 crossing nets. Six changed instance assignments persisted in the earlier all-edge 4x variant. This is evidence from one case and one seed. The 4x excess-weight attempt initially stopped at memory admission. The data uses the successful rerun with the same limit.

The official algorithm and decoder excerpts are references for inspection. The official evaluator implements the full flow and verifies every submitted result.
