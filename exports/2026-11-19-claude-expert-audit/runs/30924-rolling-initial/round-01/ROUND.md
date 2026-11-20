# 第 1 轮

实际父候选 `5470526ceb6dbd551f20e0b2d93013d371e34dc40c5500053aea86b439caa67a`。候选 `09ce1c77bee30fab1aab007c41c60230c0a0c95644da87783a40d5e56d360c45`。范围 official-runner，账本状态 failed，已取得 9/9 组，完整分 **—**。

## 模型当时可见的信息

- 事件 3，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。
- 事件 5，用途 generation。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 8，用途 generation。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 10，用途 generation。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposals。

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
    "mechanism": "Euclidean area-weighted two-means projected onto the center-difference axis with an area-cumulative median split",
    "decision": "assign dies by the signed projection threshold instead of spherical similarity to centers",
    "prediction": "the area-balanced projection cut separates weakly timed groups differently from proposal A while keeping both dies populated",
    "falsifier": "target-case paired timing does not improve or the final labels repeatedly collapse to one side."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | — | — | — |
| bp_fe-ng45 | 1002 | — | — | — |
| bp_fe-ng45 | 1003 | — | — | — |
| bp-ng45 | 1001 | — | — | — |
| bp-ng45 | 1002 | — | — | — |
| bp-ng45 | 1003 | — | — | — |
| ariane133-ng45 | 1001 | — | — | — |
| ariane133-ng45 | 1002 | — | — | — |
| ariane133-ng45 | 1003 | — | — | — |
