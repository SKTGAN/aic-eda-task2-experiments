# 第 10 轮

实际父候选 `e5cb3c4ddbbae0fb2537c825b79b53a85ff11d532ab54176ef17e0bf035fbc57`。候选 `4b3c0dc2705c3b376b52097e1cd5c8225ca1c9ff672a8bf2cdceb9b744773fb6`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **32.68**。

## 模型当时可见的信息

- 事件 68，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 70，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "5f9ad08cf1ce1d151448d56197c77b3d13da4153461faa070c54e6ca6e738aae",
  "reason": "narrow_gain",
  "improved_cases": 2,
  "regressed_cases": 1,
  "cases": 3,
  "largest_cell": {
    "case": "ariane133-ng45",
    "seed": "1002",
    "score_delta": 55.455303196059724
  },
  "largest_cell_share": 0.947
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent criticality reweighting plus a criticality Fisher-separation term. Change versus the parent: keep the parent's positive-pair worst-slack reweighting and its negative logistic objective, but add"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 39.05 | -0.84 | -281.27 |
| bp_fe-ng45 | 1002 | 35.08 | -0.89 | -302.53 |
| bp_fe-ng45 | 1003 | 55.18 | -0.58 | -228.45 |
| bp-ng45 | 1001 | -14.34 | -7.89 | -8600.62 |
| bp-ng45 | 1002 | -26.01 | -7.85 | -9909.19 |
| bp-ng45 | 1003 | -27.37 | -8.36 | -9797.47 |
| ariane133-ng45 | 1001 | 71.13 | -0.35 | -3.31 |
| ariane133-ng45 | 1002 | 82.28 | -0.22 | -1.20 |
| ariane133-ng45 | 1003 | 79.11 | -0.26 | -1.71 |
