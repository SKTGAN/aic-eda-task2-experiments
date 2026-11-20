# 第 3 轮

实际父候选 `ce56a2d8d7961bd45378b9d44dd3dcce30148d115c8f26bc614ecf9cb4ac4570`。候选 `809506cbfa75f4730e29bde73caaf06342de2cb6934da57e8e8d048eea1dda89`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **9.96**。

## 模型当时可见的信息

- 事件 25，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "broad_regression",
  "candidate_id": "57e8cc549349c019fd93e27bf502aa1eb5cae0c814cdf2a34e1e6c19833399f2",
  "regressed_pairs": 6,
  "scored_pairs": 9
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent random-walk logistic pair objective plus timing-weighted graph-star attraction. Change vs parent: add a normalized -logsigmoid(graph_scores) term weighted by graph_weights. Expected measurable "
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
| ariane133-ng45 | 1001 | -22.66 | -1.01 | -74.58 |
| ariane133-ng45 | 1002 | -35.28 | -0.43 | -165.54 |
| ariane133-ng45 | 1003 | 61.71 | -0.48 | -3.05 |
