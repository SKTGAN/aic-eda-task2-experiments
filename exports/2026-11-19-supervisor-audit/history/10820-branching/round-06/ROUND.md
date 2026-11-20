# 第 6 轮

实际父候选 `f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd`。候选 `4dd12b53a98a7c31be71c87f5d1b6174cdf811b815d87c1a21a0c1aefb8980d5`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **2.81**。

## 模型当时可见的信息

- 事件 39，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "loss",
  "incumbent_id": "f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd",
  "evidence": {
    "candidate_id": "fa9b732e2e9f7e80eb3d299e0c08fe811379003a0a8395540c73512e9e28a729",
    "score": 24.67110556452091,
    "parent_id": "f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd",
    "complete": true,
    "official_score_delta": -2.263660289008044,
    "largest_regression": {
      "case": "bp_fe-ng45",
      "seed": "1001",
      "score_delta": -18.574932016371267,
      "raw_score_contribution_deltas": {
        "wns": -13.0384,
        "tns": -5.5365
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "bp_fe-ng45",
      "seed": "1002",
      "score_delta": 5.059111964305174
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -6.790980867024131
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
        "mean_paired_score_delta": 0.0
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
  "loss": {
    "mechanism": "retain the random-walk contrastive pair loss and the parent's squared timing-weighted graph-star attraction, but gate each star edge by the geometric mean of its endpoint timing-co",
    "decision": "edges whose endpoints have unknown or partial timing coverage contribute less to the embedding gradient, so the seeded two-means tier boundary is driven by timing-observed star edg",
    "prediction": "the timing-weighted cut should fall more consistently across cases and seeds, with fewer cross-seed regressions where missing timing previously distorted the graph attraction",
    "falsifier": "matched official combined score fails to improve over the parent while the coverage gates are present and timing-weighted cut does not fall."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 47.29 | -0.70 | -258.20 |
| bp_fe-ng45 | 1002 | 44.87 | -0.79 | -240.96 |
| bp_fe-ng45 | 1003 | 62.68 | -0.60 | -128.91 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 1.10 | -0.86 | -55.03 |
| ariane133-ng45 | 1002 | -100.00 | -0.49 | -305.95 |
| ariane133-ng45 | 1003 | 9.48 | -0.51 | -83.45 |
