# 第 2 轮

实际父候选 `published-official-initial`。候选 `f55632ef21ea1dec668e7e82b2e97780bd7a071b9bbc50cbfca4541975c778bb`。范围 diagnostic，账本状态 succeeded，已取得 3/3 组，完整分 **-3.89**。

## 模型当时可见的信息

- 事件 8，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 10，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "test_alternative_component_after_opening",
  "evidence": {
    "reason": "partition_mostly_unchanged",
    "identical_assignments": 2,
    "kept_up_to_swap": 2,
    "die_swaps": 0
  },
  "largest_regression": {
    "case": "ariane133-ng45",
    "seed": "1002",
    "score_delta": -18.596710836516653,
    "raw_score_contribution_deltas": {
      "wns": 13.7659,
      "tns": -32.3626
    }
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Change vs parent: replace the single frozen helper call with a bounded custom area-weighted two-center k-means. Initialization is deterministic from the weighted embedding mean and farthest embedding;"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1002 | 52.84 | -0.65 | -219.15 |
| bp-ng45 | 1002 | -40.18 | -7.89 | -11449.92 |
| ariane133-ng45 | 1002 | -24.34 | -0.55 | -132.46 |
