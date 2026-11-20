# Literature notes for the Harness audit

The following sources suggest methods to adapt. Their reported benchmarks and
budgets differ from this contest. They do not establish that any suggested
Harness patch will improve the EDA score.

| Primary source | What it contributes | Concrete use in this audit |
|---|---|---|
| [ReEvo, Ye et al., 2024, section 4](https://arxiv.org/html/2402.01145#S4) | Compares two evaluated heuristics, uses short-term reflection to guide crossover, and summarizes lessons over time. Its paper also reports component ablations in section 6.2. | Keep deterministic paired facts and a short set of supported lessons keyed by mechanism. Use reflection to formulate a falsifiable follow-up, with the evidence ID retained. Do not use a model-written explanation as experimental proof. |
| [AlphaEvolve, Novikov et al., 2025](https://arxiv.org/abs/2506.13131) | Stores evaluated programs, samples from the archive and evaluates generated edits through an external evaluator. | Retain a small set of distinct branch parents and separate final winner selection from sampling the next parent. Offer exact, traceable component edits as potential recombination material drawn from the current run. |
| [Compute Allocation for Self-Evolving LLMs, Xing et al., 2026 preprint](https://arxiv.org/abs/2605.29268v3) | Studies allocating a fixed amount of model compute to breadth versus depth and routing compute across parallel trajectories. | Compare one deep planning call at an uncertain branch point against ordinary low-effort refinement in a cost-matched experiment. With only ten scored candidates, use explicit triggers before adopting a heavyweight bandit. |
| [NIST Engineering Statistics Handbook, full factorial designs](https://www.itl.nist.gov/div898/handbook/pri/section3/pri333.htm) and [two-way factorial model](https://itl.nist.gov/div898/handbook/prc/section4/prc437.htm) | Separates main effects and interaction effects under matched factor levels. Two binary factors need four settings and three need eight for a complete factorial experiment. | Check the exact `P, A, B, AB` components and compare matched seeds. A selective schedule saves budget but leaves some interaction terms unidentified. |
| [TP-GNN, Lu et al., DAC 2020](https://gtcad.gatech.edu/www/papers/DAC20_TP-GNN.pdf) and [Differentiable Timing-Aware Tier Partitioning with Hypergraph Extension, ISEDA 2026](https://ieeexplore.ieee.org/abstract/document/11751497) | TP-GNN separates learned graph representation and area-aware clustering. The 2026 work treats timing, cross-tier connections, and area balance jointly using slack-weighted virtual edges on an extended hypergraph. | Treat the loss-to-embedding, embedding-to-assignment, and assignment-to-timing steps as distinguishable hypotheses. Use their available observations or experiments to spot where a proposal has no effect. Slack-weighted attraction is a research hypothesis under the existing interface; the contest's fixed inputs and evaluator stay fixed. |

The highest-priority synthesis is a small evaluator-grounded loop: compile
evidence in code, ask the model to design one discriminating experiment, run an
appropriate candidate gate, then update the measured candidate archive. The
documents in this bundle describe this proposed combination and the limits of
the existing evidence.
