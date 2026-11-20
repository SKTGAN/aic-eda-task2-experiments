# 第 4 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `d5fd4448ad8d57fe652cc16b641a1d5002fa11145f699750b888cf1728df62ca`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **29.67**。

## 模型当时可见的信息

- 事件 24，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 26，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "c2dbfe1748424d91f05dab0c38ab867ecd532072632e44c6e235b773f12e15c5",
  "reason": "partition_mostly_unchanged",
  "identical_assignments": 3,
  "kept_up_to_swap": 6,
  "die_swaps": 0,
  "next_step": "strengthen_the_loss_term_so_labels_move"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Add a stronger timing-weighted star-edge attraction term to the parent loss. Change relative to the parent: keep the sampled random-walk log-sigmoid contrastive objective unchanged, and add a normaliz"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 41.09 | -0.80 | -281.76 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -13.82 | -7.87 | -8552.39 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -2.53 | -7.91 | -7284.26 |
| ariane133-ng45 | 1001 | 43.44 | -0.65 | -12.40 |
| ariane133-ng45 | 1002 | 68.47 | -0.38 | -4.34 |
| ariane133-ng45 | 1003 | 70.27 | -0.25 | -16.90 |
