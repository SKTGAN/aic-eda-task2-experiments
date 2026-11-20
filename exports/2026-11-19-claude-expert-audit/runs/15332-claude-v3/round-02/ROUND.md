# 第 2 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `e8b9aeca79584d264933a52656a5762dc26b628870d352c39e3ec1c89ae7efe0`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **0.83**。

## 模型当时可见的信息

- 事件 8，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 10，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。
- 事件 13，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "test_alternative_component_after_opening",
  "evidence": {
    "reason": "partition_mostly_unchanged",
    "identical_assignments": 4,
    "kept_up_to_swap": 8,
    "die_swaps": 0
  },
  "largest_regression": {
    "case": "bp_fe-ng45",
    "seed": "1001",
    "score_delta": -27.284925266225567,
    "raw_score_contribution_deltas": {
      "wns": -14.7623,
      "tns": -12.5226
    }
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Replace the parent reference-helper call with a custom area-targeted two-center loop. Change vs parent: deterministic farthest-point two-center initialization, bounded area-weighted center updates, th"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 41.85 | -0.83 | -253.64 |
| bp_fe-ng45 | 1002 | 30.71 | -0.88 | -358.36 |
| bp_fe-ng45 | 1003 | 54.90 | -0.68 | -178.68 |
| bp-ng45 | 1001 | -13.26 | -7.92 | -8466.77 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -4.59 | -7.88 | -7530.42 |
| ariane133-ng45 | 1001 | -22.66 | -1.01 | -74.58 |
| ariane133-ng45 | 1002 | -100.00 | -0.68 | -413.93 |
| ariane133-ng45 | 1003 | 44.97 | -0.51 | -26.29 |
