# 第 3 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `c2dbfe1748424d91f05dab0c38ab867ecd532072632e44c6e235b773f12e15c5`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **24.48**。

## 模型当时可见的信息

- 事件 17，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 19，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "e8b9aeca79584d264933a52656a5762dc26b628870d352c39e3ec1c89ae7efe0",
  "reason": "orientation_only",
  "identical_assignments": 2,
  "kept_up_to_swap": 5,
  "die_swaps": 6
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Use a timing-weighted margin attraction on graph star edges. Change relative to the parent: keep the maintained random-walk positive/negative log-sigmoid contrastive term, and add a normalized timing-"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -13.82 | -7.87 | -8552.39 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -2.53 | -7.91 | -7284.26 |
| ariane133-ng45 | 1001 | 19.90 | -0.47 | -72.14 |
| ariane133-ng45 | 1002 | 47.61 | -0.35 | -42.00 |
| ariane133-ng45 | 1003 | 59.15 | -0.49 | -5.99 |
