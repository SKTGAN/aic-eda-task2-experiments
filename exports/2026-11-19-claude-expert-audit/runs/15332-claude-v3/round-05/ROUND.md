# 第 5 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `d85fd880eceadd2bf3e2db0b31aaa8d61fdb2ee24659c11e4006f7aa37d0284a`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **5.58**。

## 模型当时可见的信息

- 事件 31，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 33，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。
- 事件 36，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。
- 事件 39，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, evaluations_remaining, previous_generation_issue, experiment_plan, largest_regression, prior_trials。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "d5fd4448ad8d57fe652cc16b641a1d5002fa11145f699750b888cf1728df62ca",
  "reason": "partition_mostly_unchanged",
  "identical_assignments": 2,
  "kept_up_to_swap": 6,
  "die_swaps": 0
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Replace the parent's single reference_global_two_way handoff with one bounded custom two-center loop whose assignment step is a global area-balanced sweep. Change vs parent: instead of per-node neares"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 36.02 | -0.90 | -284.93 |
| bp_fe-ng45 | 1002 | 46.61 | -0.72 | -257.91 |
| bp_fe-ng45 | 1003 | 54.87 | -0.69 | -174.31 |
| bp-ng45 | 1001 | -13.26 | -7.92 | -8466.77 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -4.59 | -7.88 | -7530.42 |
| ariane133-ng45 | 1001 | -22.66 | -1.01 | -74.58 |
| ariane133-ng45 | 1002 | -100.00 | -0.64 | -441.15 |
| ariane133-ng45 | 1003 | 77.74 | -0.28 | -1.71 |
