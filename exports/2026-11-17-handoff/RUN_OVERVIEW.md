# Server comparison

Server 1 runs the Claude revision. Server 2 runs our previous optimized Harness.
Published loss_decoder initial training score: 20.4251. This is not a same-host baseline.
All candidates use the same official three-case, nine-cell training grid.
The two snapshots were taken at different times.

## server-1-claude

Captured 2026-11-17 21:33:56 UTC+08.
5 submitted candidates; 4 completed feedback records.
This running Harness did not record request or reply bodies. Its full recorded decision trace, visible review verdicts, token/cost accounting, candidate source, and physical receipts are included.

| Round | Score or progress | Search decision | Changed function and mechanism | Minutes | Request ID prefix |
|---:|---:|---|---|---:|---|
| 1 | 11.94 | opening_control | decoder: Replace the frozen two-means decoder with an area-balanced principal-axis split. Relative to the parent, this keeps the same legal area-balanced top-die fill but ranks groups by a power-iteration proj | 109.7 | e-e88082bdac994 |
| 2 | 29.43 | opening_control | loss: Relative to the parent (random-walk contrastive loss only), add a timing-weighted star-edge attraction term sum_e w_e * softplus(-graph_scores_e) / sum_e w_e rescaled by (P+Q)/source_batch_size so its | 111.2 | e-b6617f1892d2d |
| 3 | 24.87 | refine_incumbent | loss: Relative to the parent loss, keep the timing-weighted star-edge attraction sum_e w_e * softplus(-graph_scores_e) but focus each edge by the endpoint timing criticality read from published node_feature | 115.4 | e-a83b78148bfc5 |
| 4 | 34.75 | explore_from_incumbent | decoder: Relative to the parent, keep the timing-weighted star-edge loss unchanged and replace the frozen two-means helper with a custom seeded area-balanced two-means decoder. Initial centers are an embedding | 113.8 | e-785401a4543c6 |
| 5 | 8/9 result files | assignment_unchanged | loss: Relative to the parent timing-weighted star-edge attraction, this substitutes an area-mobility-weighted edge mean read from the published graph endpoints and node_areas. Small movable standard-cell su | - | e-613cfc9f92dc2 |

See rounds/ for lineage, programs/ for the full accepted source,
physical-cells.csv for normalized timing comparisons, and evaluations/ for original receipts.
Provisional rows are not complete candidate scores.

## server-2-local-harness

Captured 2026-11-17 21:36:35 UTC+08.
4 submitted candidates; 3 completed feedback records.
11 recorded model requests and 11 visible replies. The log contains response text and available usage, not hidden reasoning.

| Round | Score or progress | Search decision | Changed function and mechanism | Minutes | Request ID prefix |
|---:|---:|---|---|---:|---|
| 1 | 5.48 | opening_control | decoder: Parent delegates to reference_global_two_way. This version changes the decoder to a deterministic area-balanced embedding sweep refined by bounded capacity-constrained Lloyd updates: each step ranks n | 122.1 | e-add2a2f638cec |
| 2 | 18.22 | opening_control | loss: Parent random-walk pair objective with timing/area pair reweighting. Mechanism: keep the parent logistic positive/negative pair geometry, but weight each sampled pair by endpoint timing-criticality an | 115.7 | e-68ae1bb971200 |
| 3 | 9.96 | broad_regression | loss: Parent random-walk logistic pair objective plus timing-weighted graph-star attraction. Change vs parent: add a normalized -logsigmoid(graph_scores) term weighted by graph_weights. Expected measurable | 121.7 | e-a9b6429809e50 |
| 4 | 5/9 result files | partition_mostly_unchanged | loss: Margin-hinge bifurcation objective instead of the parent soft logistic. Change vs the parent initial program: the parent's logistic pair objective is replaced by a hard hinge margin (0.5) on the sampl | - | e-f689f56365fbe |

See rounds/ for lineage, programs/ for the full accepted source,
physical-cells.csv for normalized timing comparisons, and evaluations/ for original receipts.
Provisional rows are not complete candidate scores.

## Reading the English copy

One Chinese expert heading and its three paragraphs in Server 2 were translated in the Harness and the corresponding logged prompt. Numerical results, candidate source, later prompt text, and the rest of the interaction records were retained. Original source hashes are recorded. Actual model content absent at source remains absent here.

Candidate code and offline data in the archive are for development review. Only the declared expert section and current run evidence belong in a new competitive agent call.
