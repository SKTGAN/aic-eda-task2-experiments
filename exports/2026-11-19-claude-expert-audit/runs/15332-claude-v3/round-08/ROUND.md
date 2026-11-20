# 第 8 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `3c10a34e6a7fd1bace5543a0f807181b16f2495ded9d557bbc720b45114096c8`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **23.08**。

## 模型当时可见的信息

- 事件 57，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 59，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "timing_mostly_unchanged",
  "unchanged_pairs": 6,
  "evidence_candidate_id": "036d42dfd580f2c7d346388b33711c65ba11773bfc30de875403dd98b858b018"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Add a moderately scaled timing-weighted star attraction to the parent loss. Relative to the parent pure random-walk log-sigmoid objective, this keeps the sampled positive/negative contrastive term unc"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -20.55 | -7.87 | -9293.23 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 61.94 | -0.47 | -3.54 |
| ariane133-ng45 | 1002 | -8.28 | -0.53 | -109.75 |
| ariane133-ng45 | 1003 | 68.20 | -0.38 | -4.51 |
