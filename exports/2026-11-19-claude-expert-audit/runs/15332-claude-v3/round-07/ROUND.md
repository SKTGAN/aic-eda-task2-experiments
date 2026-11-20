# 第 7 轮

实际父候选 `d5fd4448ad8d57fe652cc16b641a1d5002fa11145f699750b888cf1728df62ca`。候选 `036d42dfd580f2c7d346388b33711c65ba11773bfc30de875403dd98b858b018`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **22.76**。

## 模型当时可见的信息

- 事件 48，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 50，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。
- 事件 53，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "follow_up_case_champion",
  "protect_case_seeds": {
    "ariane133-ng45": [
      "1001",
      "1002",
      "1003"
    ]
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Refine the parent reference partition with one area-aware Lloyd correction. Change relative to the parent: still call the trusted reference helper exactly once with unchanged inputs to obtain a legal,"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 21.85 | -0.94 | -432.89 |
| bp_fe-ng45 | 1002 | 41.09 | -0.80 | -281.76 |
| bp_fe-ng45 | 1003 | 47.33 | -0.66 | -281.44 |
| bp-ng45 | 1001 | -13.82 | -7.87 | -8552.39 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -2.53 | -7.91 | -7284.26 |
| ariane133-ng45 | 1001 | 43.44 | -0.65 | -12.40 |
| ariane133-ng45 | 1002 | 21.66 | -0.37 | -81.30 |
| ariane133-ng45 | 1003 | 70.27 | -0.25 | -16.90 |
