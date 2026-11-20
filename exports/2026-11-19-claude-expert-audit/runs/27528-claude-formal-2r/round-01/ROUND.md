# 第 1 轮

实际父候选 `4fe0feef55b74d9f50277f0654a69215cff43e30c68997f8728dac4b4052a1a8`。候选 `cdf71ef54897fda5243997c5632b9d4d137e91781eeb710ab8aad5638d4b6fef`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **1.79**。

## 模型当时可见的信息

- 事件 1，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue。
- 事件 3，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "opening_control"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent logistic pair loss plus a timing-weighted star-edge cut proxy. Change relative to the parent: keep the random-walk logistic objective unchanged and add a small normalized penalty sum(graph_weig"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 56.00 | -0.66 | -174.72 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -20.55 | -7.87 | -9293.23 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | -22.66 | -1.01 | -74.58 |
| ariane133-ng45 | 1002 | 25.59 | -0.51 | -57.76 |
| ariane133-ng45 | 1003 | -100.00 | -0.85 | -440.24 |
