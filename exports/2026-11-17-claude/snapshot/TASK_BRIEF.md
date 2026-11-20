# Contest Task 2 in English

## The deliverable is an autonomous search harness

The contest provides a gate-level netlist and a fixed two-tier 3D physical-design flow. The circuit has a fixed logical function and fixed connectivity. A candidate chooses which die holds each instance. The evaluator checks the partition, runs placement and power-network construction, assigns cross-die terminals, performs physical timing optimization, and measures setup timing before clock-tree synthesis. Timing can change even when the number of cut nets is unchanged.

Build a harness with an Agent.run(context) entry point. It starts from the official initial algorithm, calls the metered official model to propose valid functions, submits candidates, interprets experimental feedback, selects the next search direction, and returns the ID of a candidate with a complete verified training matrix. The organizers rerun the submitted harness from the official starting point under the common budget. The core task is to build the search procedure that discovers improved algorithms.

## Editable algorithm and fixed flow

This package uses the loss_decoder baseline. Candidates can edit compute_tp_gnn_loss, decode_tp_gnn_embeddings, or both, with the original signatures. The initial loss uses the frozen positive and negative samples. The loss can access published timing tensors. The decoder can access embeddings, node areas, seed, iteration limit, and area target. The reference decoder uses seeded, area-balanced, area-weighted two-means and deterministic rounding. It returns one binary die label per group. Protected feasibility repair enforces legal assignments. The top die must contain 47 to 53 percent of total instance area. With macros present, the top die must contain 45 to 55 percent of macro count and macro area. The graph, sampling, optimizer, physical inputs, flow, and evaluator are fixed.

## Scoring and budget

WNS measures the worst setup timing violation. TNS sums negative setup slack across constrained endpoints. The score uses 40 percent normalized WNS improvement and 60 percent normalized TNS improvement against published per-design references. The floor is -100 per case-and-seed pair, including verified physical failures. An official candidate evaluation covers three training designs and three seeds, for nine physical runs. A formal run allows up to ten candidate submissions and CNY 15 in model calls through the official DeepSeek-V4.1-Flash gateway. The final contest result aggregates seven designs, including training, public validation, and hidden designs.

General offline expertise is declared in the opening prompt under the 200-unit limit. The harness learns from the official task materials and the current run's feedback. Keep the offline candidate programs and results in the development review area.

[Official contest page and rulebook](https://www.aicomp.cn/tracks/tracks-4/5590.html)
