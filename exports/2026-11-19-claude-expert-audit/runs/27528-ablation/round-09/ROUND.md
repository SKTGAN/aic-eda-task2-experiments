# 第 9 轮

实际父候选 `1419acdef89f42cf77febf4669e8a8f48665755853884d7ee31b30de8888d09a`。候选 `e0e90f7dde923296163e7a38e49eeb9bb7b6ce7ba96eb37ae36f594d76f4d1d2`。范围 official-runner，账本状态 accepted，已取得 8/9 组，完整分 **—**。

## 模型当时可见的信息

- 事件 57，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 59，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "7c738240bdcd16b2a057adfb427494fcb9286dd1da88e6e9d3c774fad53ec6b1",
  "reason": "partition_mostly_unchanged",
  "identical_assignments": 3,
  "kept_up_to_swap": 5,
  "die_swaps": 0,
  "next_step": "strengthen_the_loss_term_so_labels_move"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent: maintained random-walk pair logsigmoid objective only. Change relative to the parent: retain that exact positive/negative logsigmoid pair term and add a timing-weighted, weight-normalized soft"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1003 | 0.00 | -0.64 | -188.35 |
| bp_fe-ng45 | 1002 | 0.00 | -0.73 | -211.75 |
| bp_fe-ng45 | 1001 | 0.00 | -0.66 | -174.72 |
| bp-ng45 | 1003 | 8.31 | -7.91 | -7399.59 |
| bp-ng45 | 1002 | 3.43 | -7.88 | -9726.86 |
| bp-ng45 | 1001 | 0.93 | -7.87 | -9293.23 |
| ariane133-ng45 | 1002 | -12.65 | -0.61 | -108.67 |
| ariane133-ng45 | 1001 | -69.22 | -0.86 | -36.06 |
