# 第 5 轮

实际父候选 `1158d4c5d9ab996a249ea70f3943a9effc42bb871010750a20a2b20c42a8e877`。候选 `237785f66d66555a0b10397823e8ec85b1dfd8d12613a8efc6af9d4327048f77`。范围 official-runner，账本状态 accepted，已取得 4/9 组，完整分 **—**。

## 模型当时可见的信息

- 事件 48，用途 plan。可读输入字段 options, triggers, lessons, anchor_review, budget, allowed_probes。
- 事件 51，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment, experiment_plan。
- 事件 54，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment, experiment_plan。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "decoder",
  "rolling_plan_override": true,
  "experiment": {
    "id": "X2",
    "kind": "edit",
    "question": "Is a decoder change of R1 more promising than the edit above?"
  },
  "evidence": {
    "candidate_id": "8f2d565aa91c9f82047e47f5427c7ea71300b34822f1fc8240f3436de74a2229",
    "score": -1.893790116858245,
    "parent_id": "5470526ceb6dbd551f20e0b2d93013d371e34dc40c5500053aea86b439caa67a",
    "complete": true,
    "official_score_delta": -22.3188504331202,
    "largest_regression": {
      "case": "ariane133-ng45",
      "seed": "1001",
      "score_delta": -107.70955636364361,
      "raw_score_contribution_deltas": {
        "wns": 3.0732,
        "tns": -110.7828
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "ariane133-ng45",
      "seed": "1002",
      "score_delta": 21.31524193451264
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -9.094975088741856
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 2.4910752227747204
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -60.35265143339347
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
    "mechanism": "area-weighted Euclidean two-means on L2 embeddings replaces spherical center normalization",
    "decision": "choose each split by ranking the center-distance margin and cutting at the area-balanced cumulative quantile, with orientation inherited from the area-weighted variance direction",
    "prediction": "bp_fe-ng45 mean paired score rises and most of its seeds improve versus R1 while bp-ng45 and ariane133-ng45 stay within the protected tolerances",
    "falsifier": "bp_fe-ng45 mean paired delta is non-positive, or bp-ng45 mean falls below -5, or ariane133-ng45 mean falls below -37.246 versus R1."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1003 | 1.48 | -0.69 | -174.31 |
| bp_fe-ng45 | 1002 | 0.00 | -0.73 | -211.75 |
| bp_fe-ng45 | 1001 | -46.17 | -0.63 | -314.46 |
| bp-ng45 | 1001 | 8.08 | -8.16 | -8007.85 |
