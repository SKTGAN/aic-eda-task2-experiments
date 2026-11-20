# 第 4 轮

实际父候选 `ce56a2d8d7961bd45378b9d44dd3dcce30148d115c8f26bc614ecf9cb4ac4570`。候选 `16f9f230807fe0ed8b333bd3ce0dd9b0af925003fdac8f5da4e50bd6ed10143a`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **1.12**。

## 模型当时可见的信息

- 事件 29，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。
- 事件 32，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。
- 事件 35，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "partition_mostly_unchanged",
  "candidate_id": "809506cbfa75f4730e29bde73caaf06342de2cb6934da57e8e8d048eea1dda89",
  "identical_assignments": 6
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Margin-hinge bifurcation objective instead of the parent soft logistic. Change vs the parent initial program: the parent's logistic pair objective is replaced by a hard hinge margin (0.5) on the sampl"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 33.02 | -0.87 | -336.95 |
| bp_fe-ng45 | 1002 | 31.18 | -0.91 | -340.33 |
| bp_fe-ng45 | 1003 | 59.11 | -0.66 | -138.00 |
| bp-ng45 | 1001 | -22.07 | -7.87 | -9463.66 |
| bp-ng45 | 1002 | -30.62 | -7.86 | -10413.49 |
| bp-ng45 | 1003 | -22.18 | -7.88 | -9471.47 |
| ariane133-ng45 | 1001 | -44.59 | -0.57 | -162.76 |
| ariane133-ng45 | 1002 | 74.85 | -0.29 | -5.21 |
| ariane133-ng45 | 1003 | -68.66 | -0.70 | -185.72 |
