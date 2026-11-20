# 第 6 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `505eb144a47a0e993a23886878d7f6367ae8fda3172647066983daeb8fff751c`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **23.70**。

## 模型当时可见的信息

- 事件 43，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 45，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "d85fd880eceadd2bf3e2db0b31aaa8d61fdb2ee24659c11e4006f7aa37d0284a",
  "reason": "orientation_only",
  "identical_assignments": 2,
  "kept_up_to_swap": 7,
  "die_swaps": 6
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Add a graph_weights-normalized timing-star attraction to the parent loss. Change relative to the parent: keep the parent sampled random-walk log-sigmoid contrastive objective unchanged, and add the we"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -6.18 | -7.93 | -7679.81 |
| ariane133-ng45 | 1001 | 32.68 | -0.69 | -24.74 |
| ariane133-ng45 | 1002 | 52.18 | -0.46 | -20.40 |
| ariane133-ng45 | 1003 | 36.68 | -0.62 | -26.26 |
