# Speed and deadline plan

1. Save the two run snapshots and archive the best complete candidate with its corresponding Harness. The existing loss_decoder comparison took about two hours per completed 9-cell candidate on our server. Preserve Server 1's leading result and prioritize its public validation once that Harness selects and freezes its final candidate. Keep the physical files required for the entry.
2. Screen the revised Harness on the weakest published seed (1002) of each of the three training cases. Use the same panel for three sequential candidates: 9 physical cells in total versus 27. A quicker alternative is a 3-cell matched initial-program control followed by two rounds; use the control first if host drift would otherwise decide the result. Maximize learning, not the sampled average. Keep both per-seed deltas and the worst case. Two seeds per case is an optional second screen, not the default.
3. Check generated source and output constraints before sending to the evaluator. Where cached validated embeddings are available, compare decoder-only layer assignments and their label-swapped distance cheaply in isolation. That is a rejection signal only: it cannot assess physical timing, loss training, or all cases.
4. Promote at most one promising version into a clean run with the full 9-cell training matrix. Approve a final version from comparable complete receipts, not the small panel or the public validation data. Freeze before running the six public validation cells. If the revision does not show a decisive improvement, fall back to the stronger completed Harness rather than continue open-ended tuning.
5. With two available GPUs, use one for the known-strong full/validation path and the other for 3-cell screening. These are separate runs; consecutive candidates still depend on feedback. If budget is tight, prioritize preserving the strong run and leave the last day for exports, checking the README and log, and submitting.

Example development command on an idle Linux GPU host, from the archive root:

    python3 -B development/diagnose_harness.py --official /path/to/official --plan
    python3 -B development/diagnose_harness.py --official /path/to/official --runtime /path/to/runtime.json --api-key-file /private/key-file --work-root /path/to/new-diagnostic-work

Use a separate work directory. The diagnostic runner uses the released development evaluator but its sampled results cannot be used as formal scores. The three rounds share the 15 RMB independent model budget; GPU rental is separate. Physical cell count falls 67%; actual wall time need not scale linearly. No new live run is included with this archive.
