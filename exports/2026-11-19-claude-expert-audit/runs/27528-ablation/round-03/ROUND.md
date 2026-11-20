# 第 3 轮

实际父候选 `012b248b2d2ccd254d3810d4db80168ec60b0329e05de107004d3437e346a746`。候选 `5b979eeb4cf4c9f649ec055bd9e35c2d11109f2ad57b507505612e81baa6e2d2`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **12.76**。

## 模型当时可见的信息

- 事件 14，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 16，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。
- 事件 19，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。
- 事件 22，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "keep_measured_ablation_control",
  "ablation_result": {
    "status": "failed",
    "target_gain": 80.51360601775308,
    "protected_losses": [
      {
        "case": "ariane133-ng45",
        "seed": "1002",
        "score_delta": -157.7846167448366
      }
    ],
    "case_mean_losses": {
      "ariane133-ng45": -25.757003575694508
    },
    "score_delta": -8.585667858564836
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Replace the parent helper call with one bounded custom area-balanced loop. Relative to the parent decoder, this keeps two-center area-weighted means but performs a fixed number of Lloyd-style refineme"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 52.59 | -0.63 | -231.69 |
| bp_fe-ng45 | 1002 | 49.92 | -0.69 | -232.29 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -24.05 | -7.83 | -9702.88 |
| bp-ng45 | 1002 | -40.18 | -7.89 | -11449.92 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 66.56 | -0.30 | -16.82 |
| ariane133-ng45 | 1002 | 57.78 | -0.50 | -7.42 |
| ariane133-ng45 | 1003 | -100.00 | -0.85 | -440.24 |
