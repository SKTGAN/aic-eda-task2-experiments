# 第 3 轮

实际父候选 `57ea753c16a7a4d103c6a77b209d69f8c2659cecc440bd5b76eb4e4ca2643916`。候选 `7b2b7f4fc3cf05ce63fb33e044e4551f7842955c5e6d25de18f63280f83a9b2d`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **23.39**。

## 模型当时可见的信息

- 事件 18，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 20，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "203e2676d95aed3bcb076441c9947a07c3e70bbe0c0cad0a8e6f0d4ca51c7b1b",
  "reason": "orientation_only",
  "identical_assignments": 3,
  "kept_up_to_swap": 7,
  "die_swaps": 6
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent random-walk contrastive loss plus a timing-criticality alignment term. Relative to the parent, this keeps the random-walk positive/negative objective and adds a weighted regression of the first"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 30.50 | -0.94 | -330.47 |
| bp_fe-ng45 | 1002 | 37.09 | -0.81 | -323.66 |
| bp_fe-ng45 | 1003 | 53.09 | -0.61 | -237.55 |
| bp-ng45 | 1001 | -35.20 | -7.90 | -10896.86 |
| bp-ng45 | 1002 | -27.88 | -7.83 | -10124.23 |
| bp-ng45 | 1003 | -25.60 | -8.28 | -9644.32 |
| ariane133-ng45 | 1001 | 34.79 | -0.38 | -59.19 |
| ariane133-ng45 | 1002 | 88.44 | -0.15 | -0.57 |
| ariane133-ng45 | 1003 | 55.25 | -0.52 | -8.45 |
