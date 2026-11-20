# 第 1 轮

实际父候选 `published-official-initial`。候选 `d97c711283bf2b82b08548fa697e6410ded9cae57d7d0964ca7964753520bae5`。范围 diagnostic，账本状态 succeeded，已取得 3/3 组，完整分 **1.78**。

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
  "loss": "Change vs parent: retains the random-walk pair objective but adds a normalized timing-weighted star-edge cut penalty on graph_scores, using graph_weights so timing-critical represented nets are discou"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| ariane133-ng45 | 1002 | -20.10 | -0.33 | -153.01 |
