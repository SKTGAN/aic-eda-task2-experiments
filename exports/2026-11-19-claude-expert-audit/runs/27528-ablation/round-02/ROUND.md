# 第 2 轮

实际父候选 `012b248b2d2ccd254d3810d4db80168ec60b0329e05de107004d3437e346a746`。候选 `d11eee28ebad2c8493bea03bd99e8caa8ba3b91f6d299970f90db3f5e82bde18`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **-3.61**。

## 模型当时可见的信息

- 事件 8，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 10，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "test_opening_loss",
  "component": "loss",
  "ablation": {
    "diagnosis_reference": "published_initial_reference",
    "target": {
      "case": "ariane133-ng45",
      "seed": "1003",
      "score_delta": -138.09076392242855,
      "wns_slack_delta_ns": -0.2748628069614094,
      "tns_slack_delta_ns": -410.46784200060415
    },
    "protected_cells": [
      {
        "case": "ariane133-ng45",
        "seed": "1002",
        "score_delta": 59.29237713422596,
        "wns_slack_delta_ns": 0.014036328052705382,
        "tns_slack_delta_ns": 93.58221218383207
      }
    ],
    "minimum_target_gain": 2.0,
    "maximum_protected_loss": 2.0,
    "maximum_case_mean_loss": 2.0
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Replace the parent's linearly weighted star-edge soft cut with a log-bounded version. Relative to the parent, the positive/negative pair objective is unchanged. The timing-star penalty changes from `s"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 56.00 | -0.66 | -174.72 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -24.05 | -7.83 | -9702.88 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | -22.66 | -1.01 | -74.58 |
| ariane133-ng45 | 1002 | -100.00 | -0.53 | -294.36 |
| ariane133-ng45 | 1003 | -19.49 | -0.50 | -131.45 |
