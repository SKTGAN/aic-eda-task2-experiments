# 第 3 轮

实际父候选 `published-official-initial`。候选 `d7b933becb4e6777b4b00b962971667e16fac2538045c366ae39793a926cadd2`。范围 diagnostic，账本状态 succeeded，已取得 3/3 组，完整分 **30.98**。

## 模型当时可见的信息

- 事件 14，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 16，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "f55632ef21ea1dec668e7e82b2e97780bd7a071b9bbc50cbfca4541975c778bb",
  "reason": "orientation_only",
  "identical_assignments": 1,
  "kept_up_to_swap": 3,
  "die_swaps": 2
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Change vs the published parent: retain the random-walk positive/negative objective and add a timing-weighted star-edge cut penalty that is gated by endpoint timing pressure from node_features. This is"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| ariane133-ng45 | 1002 | 67.51 | -0.39 | -4.25 |
