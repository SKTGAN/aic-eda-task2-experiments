# 第 1 轮

实际父候选 `5470526ceb6dbd551f20e0b2d93013d371e34dc40c5500053aea86b439caa67a`。候选 `1158d4c5d9ab996a249ea70f3943a9effc42bb871010750a20a2b20c42a8e877`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **23.42**。

## 模型当时可见的信息

- 事件 3，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。
- 事件 6，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。
- 事件 8，用途 generation。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 11，用途 generation。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 14，用途 generation。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposals。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "opening_control",
  "component": "decoder",
  "experiment": {
    "id": "X1",
    "kind": "edit",
    "question": "Can a decoder change of S raise bp-ng45 without losing its other designs?"
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": {
    "mechanism": "replace Euclidean nearest-center rounding with area-cumulative spherical two-means on L2 embeddings",
    "decision": "choose each split by ranking a cosine-score projection and cutting at the area-balanced cumulative quantile",
    "prediction": "bp-ng45 mean paired score rises and most of its seeds improve versus the parent while other case means stay within tolerance",
    "falsifier": "bp-ng45 mean paired delta is non-positive or any case mean falls more than 5 below the parent."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 45.64 | -0.63 | -314.46 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 54.87 | -0.69 | -174.31 |
| bp-ng45 | 1001 | -10.22 | -8.16 | -8007.85 |
| bp-ng45 | 1002 | -51.95 | -7.83 | -12781.88 |
| bp-ng45 | 1003 | -9.63 | -8.21 | -7918.39 |
| ariane133-ng45 | 1001 | 50.74 | -0.46 | -22.70 |
| ariane133-ng45 | 1002 | -1.51 | -0.51 | -101.00 |
| ariane133-ng45 | 1003 | 82.90 | -0.22 | -0.94 |
