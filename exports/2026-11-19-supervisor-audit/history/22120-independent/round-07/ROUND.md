# 第 7 轮

实际父候选 `57ea753c16a7a4d103c6a77b209d69f8c2659cecc440bd5b76eb4e4ca2643916`。候选 `25dff3215881f0d183258f3dc428dfd21c55794212fd30442049e01f6d7300ea`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **3.76**。

## 模型当时可见的信息

- 事件 42，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 44，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。
- 事件 47，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。
- 事件 50，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "4d8e994feabd228f3b928557ce35254540288bfbb85f56defcfc8a24524034c4",
  "reason": "partition_mostly_unchanged",
  "identical_assignments": 5,
  "kept_up_to_swap": 7,
  "die_swaps": 0
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Change versus parent: replace the frozen reference two-means call with a deterministic area-weighted variance-axis projection followed by a cumulative-area balanced sweep. Expected effect: supernodes "
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 30.13 | -0.95 | -329.62 |
| bp_fe-ng45 | 1002 | 55.66 | -0.63 | -195.76 |
| bp_fe-ng45 | 1003 | 55.80 | -0.64 | -189.79 |
| bp-ng45 | 1001 | -20.82 | -8.39 | -9059.34 |
| bp-ng45 | 1002 | -29.97 | -7.84 | -10349.95 |
| bp-ng45 | 1003 | -14.45 | -7.87 | -8622.28 |
| ariane133-ng45 | 1001 | -100.00 | -0.41 | -274.63 |
| ariane133-ng45 | 1002 | 19.42 | -0.57 | -59.82 |
| ariane133-ng45 | 1003 | 38.09 | -0.57 | -29.77 |
