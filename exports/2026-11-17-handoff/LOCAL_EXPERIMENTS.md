# Local and development experiments

Local runs used the pinned image on a different host, often with a 6 GiB container limit. These are matched development measurements. Keep infrastructure failures and censored scores separate from physical outcomes.

- The nine hard-negative comparisons averaged +16.55 points, with 5 improvements and 4 regressions. The ariane133 result includes an initial value at the -100 floor. Do not interpret the gain as broad or transfer it to the server candidate with a different margin objective.
- The orientation swap improved bp-ng45 seed 1003 by +7.91 and hurt seed 1002 by -24.41. The ariane133 seed 1003 gain of +139.05 is measured from a floored initial score. Seed 1002 has a separate native diagnostic. Die orientation can affect timing even without changing cut topology.
- On bp_fe-ng45 seed 1003, the gap-aware decoder cut 9 fewer nets but scored -2.97 versus the matched control. The critical-positive experiment scored -5.64, and the uniform control +4.25. A proxy change is insufficient evidence for timing improvement.
- A same-host bp_fe-ng45 seed 1003 repeat produced identical timing, embedding, assignment and saved placement hashes. Use this control when interpreting host and published-reference differences elsewhere.
- Files labeled binary_loss concern another official baseline. Do not pool them with loss_decoder. Improving the pre-repair area fraction alone did not improve timing in the binary threshold experiment.

Original comparison JSON, replay diagnostics, terminal summaries and local candidate sources are under local/. Older server evidence under historical/ predates full request tracing.
