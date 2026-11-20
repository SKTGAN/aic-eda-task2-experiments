# 第 2 轮

实际父候选 `57ea753c16a7a4d103c6a77b209d69f8c2659cecc440bd5b76eb4e4ca2643916`。候选 `203e2676d95aed3bcb076441c9947a07c3e70bbe0c0cad0a8e6f0d4ca51c7b1b`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **23.42**。

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
    "identical_assignments": 6,
    "kept_up_to_swap": 8,
    "die_swaps": 0
  },
  "largest_regression": {
    "case": "ariane133-ng45",
    "seed": "1003",
    "score_delta": -94.66363987104941,
    "raw_score_contribution_deltas": {
      "wns": -14.0738,
      "tns": -80.5899
    }
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Parent calls the frozen reference two-way decoder. Change: replace that single helper call with a custom bounded area-weighted two-center refinement. It initializes along the embedding coordinate with"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 45.64 | -0.63 | -314.46 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 54.87 | -0.69 | -174.31 |
| bp-ng45 | 1001 | -10.22 | -8.16 | -8007.85 |
| bp-ng45 | 1002 | -51.95 | -7.83 | -12781.88 |
| bp-ng45 | 1003 | -9.63 | -8.21 | -7918.39 |
| ariane133-ng45 | 1001 | 50.74 | -0.46 | -22.70 |
| ariane133-ng45 | 1002 | -1.51 | -0.51 | -101.00 |
| ariane133-ng45 | 1003 | 82.90 | -0.22 | -0.94 |
