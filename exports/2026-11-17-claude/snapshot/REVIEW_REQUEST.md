# Request for Claude

Read TASK_BRIEF.md and README.md first. Your main deliverable is a concrete, drop-in harness revision that solves Task 2 by searching for better algorithms within the official budget.

1. Audit the current Agent.run, select_parent, and opening review. Identify where the harness spends evaluation submissions on weak or behaviorally equivalent mechanisms. Cite the relevant code and use the official starter and decoder implementation to check assumptions.
2. Produce a small complete patch or complete replacement files for the Agent directory. Explain the next-hypothesis policy, use of official failure evidence, mechanism diversity, and final selection rule. Add one offline replay or mocked test that would fail on the current implementation and pass on your revision.
3. Read experiments/latest_results.csv and the comparison records. Explain why the loss change moved the raw clustering but left the actual assignment and timing unchanged. Propose one plausible algorithm change and the smallest fair A/B test. State which physical timing metric it should affect and what result would falsify it.
4. Keep evaluation and accounting on the official bridge. Use the complete official training matrix for final selection. Write all returned code, documentation, and prompts in English. Write the review, patch explanation, and experimental recommendations in English. List which checks you executed and which need the physical runtime.
