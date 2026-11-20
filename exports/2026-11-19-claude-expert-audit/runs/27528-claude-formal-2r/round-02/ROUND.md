# 第 2 轮

实际父候选 `4fe0feef55b74d9f50277f0654a69215cff43e30c68997f8728dac4b4052a1a8`。候选 `c3faddaeecdf785bfb10a4228028b38a6e3674b9cab4e8125f6a9b090762b9fd`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **-0.22**。

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
    "identical_assignments": 7,
    "kept_up_to_swap": 8,
    "die_swaps": 0
  },
  "largest_regression": {
    "case": "ariane133-ng45",
    "seed": "1003",
    "score_delta": -138.09076392242855,
    "raw_score_contribution_deltas": {
      "wns": -20.7822,
      "tns": -255.4117
    }
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Replace the parent reference-helper call with one bounded custom two-center Lloyd loop. The change relative to the parent decoder is a seeded anchor plus farthest-anchor initialization followed by phy"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 21.85 | -0.94 | -432.89 |
| bp_fe-ng45 | 1002 | 48.17 | -0.66 | -270.52 |
| bp_fe-ng45 | 1003 | 49.23 | -0.68 | -245.55 |
| bp-ng45 | 1001 | -24.58 | -7.87 | -9740.21 |
| bp-ng45 | 1002 | -40.18 | -7.89 | -11449.92 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 66.56 | -0.30 | -16.82 |
| ariane133-ng45 | 1002 | -100.00 | -0.74 | -292.00 |
| ariane133-ng45 | 1003 | -19.49 | -0.50 | -131.45 |
