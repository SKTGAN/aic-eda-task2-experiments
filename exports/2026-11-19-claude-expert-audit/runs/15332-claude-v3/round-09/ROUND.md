# 第 9 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `5a8e17d5fdf84831a6be305e9b8d31be549f49f506d85a928c03bd88ec0a1270`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **22.22**。

## 模型当时可见的信息

- 事件 63，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 65，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "partition_mostly_unchanged",
  "identical_assignments": 5,
  "kept_up_to_swap": 8,
  "die_swaps": 0,
  "next_step": "strengthen_the_loss_term_so_labels_move",
  "evidence_candidate_id": "3c10a34e6a7fd1bace5543a0f807181b16f2495ded9d557bbc720b45114096c8"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Change vs parent: keep the parent's sampled log-sigmoid contrastive term, and add two geometric terms: (1) a net-weight-normalized softplus margin on timing-star edges to pull timing-critical connecte"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 51.38 | -0.66 | -229.16 |
| bp_fe-ng45 | 1002 | 56.83 | -0.73 | -127.00 |
| bp_fe-ng45 | 1003 | 61.46 | -0.66 | -110.14 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -28.29 | -7.87 | -10151.86 |
| bp-ng45 | 1003 | -6.66 | -7.94 | -7727.96 |
| ariane133-ng45 | 1001 | 22.60 | -0.89 | -16.07 |
| ariane133-ng45 | 1002 | 56.65 | -0.35 | -26.72 |
| ariane133-ng45 | 1003 | -1.93 | -0.41 | -113.44 |
