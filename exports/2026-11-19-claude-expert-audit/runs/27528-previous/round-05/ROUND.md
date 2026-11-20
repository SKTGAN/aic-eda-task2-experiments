# 第 5 轮

实际父候选 `ce56a2d8d7961bd45378b9d44dd3dcce30148d115c8f26bc614ecf9cb4ac4570`。候选 `f44af94d4e58fe9dd5cc7b6130302aff6742ec1699275771ef3142cc0169596d`。范围 official-runner，账本状态 accepted，已取得 3/9 组，完整分 **—**。

## 模型当时可见的信息

- 事件 39，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。
- 事件 42，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。
- 事件 45，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "broad_regression",
  "candidate_id": "16f9f230807fe0ed8b333bd3ce0dd9b0af925003fdac8f5da4e50bd6ed10143a",
  "regressed_pairs": 7,
  "scored_pairs": 9
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent random-walk logistic pair objective; change vs parent is an added timing-weighted graph-star alignment term on supplied star-edge dot products. Expected measurable effect: timing-critical conne"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1003 | 0.00 | -0.64 | -188.35 |
| bp_fe-ng45 | 1002 | 0.00 | -0.73 | -211.75 |
| bp_fe-ng45 | 1001 | -71.49 | -0.99 | -324.35 |
