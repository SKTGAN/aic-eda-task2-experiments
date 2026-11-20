# 第 6 轮

实际父候选 `1419acdef89f42cf77febf4669e8a8f48665755853884d7ee31b30de8888d09a`。候选 `a498b035c2cde27d0203ebf4bae6d76bf5c60cce80b3da86dbd41ef19ab8723d`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **12.53**。

## 模型当时可见的信息

- 事件 39，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 41，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "c555de2d7b1851f897f2e57f2e8d15f69976c6fa068bec0d6356836012cbfc8f",
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
  "loss": "Parent: pair-only random-walk logsigmoid objective. Change relative to the parent: retain the exact positive/negative logsigmoid pair objective, but add a timing-weighted margin-linear star-edge separ"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 42.95 | -0.74 | -288.16 |
| bp_fe-ng45 | 1002 | 36.20 | -0.88 | -292.64 |
| bp_fe-ng45 | 1003 | 60.55 | -0.56 | -172.20 |
| bp-ng45 | 1001 | -16.32 | -7.84 | -8844.27 |
| bp-ng45 | 1002 | -25.50 | -7.87 | -9841.94 |
| bp-ng45 | 1003 | -1.76 | -7.88 | -7217.33 |
| ariane133-ng45 | 1001 | 60.02 | -0.43 | -11.69 |
| ariane133-ng45 | 1002 | -82.91 | -0.80 | -196.84 |
| ariane133-ng45 | 1003 | 39.58 | -0.73 | -8.15 |
