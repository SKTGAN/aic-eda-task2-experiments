# 第 8 轮

实际父候选 `1419acdef89f42cf77febf4669e8a8f48665755853884d7ee31b30de8888d09a`。候选 `7c738240bdcd16b2a057adfb427494fcb9286dd1da88e6e9d3c774fad53ec6b1`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **-6.08**。

## 模型当时可见的信息

- 事件 51，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 53，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "start_still_ahead"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent keeps only the random-walk pair objective. This version keeps that positive/negative logsigmoid term and adds a timing-weighted graph attraction term: strongly connected star edges are pulled t"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -6.18 | -7.93 | -7679.81 |
| ariane133-ng45 | 1001 | 8.00 | -0.35 | -104.89 |
| ariane133-ng45 | 1002 | -54.46 | -0.45 | -194.14 |
| ariane133-ng45 | 1003 | -100.00 | -0.81 | -469.84 |
