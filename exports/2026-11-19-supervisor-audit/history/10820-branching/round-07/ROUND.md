# 第 7 轮

实际父候选 `08b8f9bd6d7e32cd8393889320eeb5debf0596766599d90efcc74e3b8fd4f741`。候选 `57c5e845b54c134ab99172798af1d972538b93b179dc3b61dc6318d1f616e297`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **23.85**。

## 模型当时可见的信息

- 事件 43，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "switch_branch",
  "component": "decoder",
  "incumbent_id": "f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd",
  "stalled_children": [
    "fa9b732e2e9f7e80eb3d299e0c08fe811379003a0a8395540c73512e9e28a729",
    "4dd12b53a98a7c31be71c87f5d1b6174cdf811b815d87c1a21a0c1aefb8980d5"
  ],
  "trigger": "two_unsuccessful_children",
  "evidence": {
    "candidate_id": "4dd12b53a98a7c31be71c87f5d1b6174cdf811b815d87c1a21a0c1aefb8980d5",
    "score": 2.812886665360599,
    "parent_id": "f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd",
    "complete": true,
    "official_score_delta": -24.121879188168357,
    "largest_regression": {
      "case": "ariane133-ng45",
      "seed": "1002",
      "score_delta": -90.03474863124042,
      "raw_score_contribution_deltas": {
        "wns": -3.8925,
        "tns": -113.23
      },
      "score_floor_delta_points": 27.0877
    },
    "largest_gain": null,
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 0.0
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 0.0
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -72.36563756450506
      }
    ],
    "gains_across_seeds": [],
    "timing_attribution_unconfirmed": [],
    "failures": []
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": {
    "mechanism": "preserve the frozen seeded area-balanced two-means handoff, then apply bidirectional high-margin wrong-side micro-flips with independent per-direction area and count caps",
    "decision": "a group changes tier only when it is closer to the opposite area-weighted center, and top-to-bottom and bottom-to-top moves are budgeted separately so one direction cannot consume ",
    "prediction": "timing-weighted cut and combined score should improve where the parent one-sided micro-flip left boundary groups unbalanced, with smaller cross-seed regressions than a single share",
    "falsifier": "matched official combined score fails to improve while the selected bidirectional flips are present or the timing-weighted cut does not fall."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 39.57 | -0.81 | -290.96 |
| bp_fe-ng45 | 1002 | 49.49 | -0.67 | -248.28 |
| bp_fe-ng45 | 1003 | 52.32 | -0.64 | -229.72 |
| bp-ng45 | 1001 | -20.55 | -7.87 | -9293.23 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 61.94 | -0.47 | -3.54 |
| ariane133-ng45 | 1002 | -8.28 | -0.53 | -109.75 |
| ariane133-ng45 | 1003 | 68.20 | -0.38 | -4.51 |
