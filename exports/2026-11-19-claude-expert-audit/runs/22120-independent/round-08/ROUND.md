# 第 8 轮

实际父候选 `57ea753c16a7a4d103c6a77b209d69f8c2659cecc440bd5b76eb4e4ca2643916`。候选 `e5cb3c4ddbbae0fb2537c825b79b53a85ff11d532ab54176ef17e0bf035fbc57`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **25.58**。

## 模型当时可见的信息

- 事件 54，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 56，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "25dff3215881f0d183258f3dc428dfd21c55794212fd30442049e01f6d7300ea",
  "reason": "orientation_only",
  "identical_assignments": 4,
  "kept_up_to_swap": 6,
  "die_swaps": 3
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent random-walk contrastive loss with coverage-masked criticality reweighting. Change versus the parent: keep the same positive/negative logistic objective, but reweight each positive pair by the s"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 56.00 | -0.66 | -174.72 |
| bp_fe-ng45 | 1002 | 41.13 | -0.74 | -310.50 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -12.90 | -8.38 | -8191.34 |
| bp-ng45 | 1002 | -29.97 | -7.84 | -10349.95 |
| bp-ng45 | 1003 | -6.98 | -7.96 | -7750.49 |
| ariane133-ng45 | 1001 | 39.06 | -0.66 | -18.34 |
| ariane133-ng45 | 1002 | 26.18 | -0.31 | -80.90 |
| ariane133-ng45 | 1003 | 61.89 | -0.45 | -7.14 |
