# 第 9 轮

实际父候选 `e5cb3c4ddbbae0fb2537c825b79b53a85ff11d532ab54176ef17e0bf035fbc57`。候选 `5f9ad08cf1ce1d151448d56197c77b3d13da4153461faa070c54e6ca6e738aae`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **32.09**。

## 模型当时可见的信息

- 事件 61，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 63，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "refine_best"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Refine parent criticality reweighting with negative-pair criticality gating. Change versus the parent: keep the exact positive-pair worst-slack reweighting, but add a coverage-masked criticality weigh"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 39.90 | -0.73 | -331.65 |
| bp_fe-ng45 | 1002 | 40.22 | -0.88 | -249.64 |
| bp_fe-ng45 | 1003 | 45.95 | -0.69 | -279.73 |
| bp-ng45 | 1001 | -10.34 | -8.30 | -7949.56 |
| bp-ng45 | 1002 | -25.17 | -7.85 | -9814.06 |
| bp-ng45 | 1003 | -1.63 | -7.92 | -7181.16 |
| ariane133-ng45 | 1001 | 79.88 | -0.25 | -1.51 |
| ariane133-ng45 | 1002 | 81.64 | -0.23 | -1.23 |
| ariane133-ng45 | 1003 | 38.39 | -0.72 | -11.21 |
