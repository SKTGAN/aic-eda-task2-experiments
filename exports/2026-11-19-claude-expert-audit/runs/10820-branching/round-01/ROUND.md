# 第 1 轮

实际父候选 `1a194e1aaad116986e5e6ec892ec2d23389d8d44616d54aaebf5b7f34cdd32cc`。候选 `ab93edc407d167411e33901f39e5b79bce15bdbff6371832981b6988474fb27e`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **12.10**。

## 模型当时可见的信息

- 事件 1，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。
- 事件 3，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 6，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 9，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposals。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "opening_control",
  "component": "decoder"
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": {
    "mechanism": "deterministic area-quantile cut on the mean-center discriminant after area-weighted Lloyd refinement",
    "decision": "the tier boundary is set by cumulative physical area at balance_target instead of nearest-center whole-group rounding",
    "prediction": "this reorders only groups near the area median and should improve combined timing when the parent rounding left the final partition off the area target",
    "falsifier": "matched-case combined score fails to improve while labels and timing-weighted cut remain unchanged."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 38.47 | -0.90 | -255.98 |
| bp_fe-ng45 | 1002 | 35.28 | -0.73 | -385.20 |
| bp_fe-ng45 | 1003 | 39.49 | -0.74 | -328.26 |
| bp-ng45 | 1001 | -20.55 | -7.87 | -9293.23 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 66.56 | -0.30 | -16.82 |
| ariane133-ng45 | 1002 | -100.00 | -0.64 | -441.15 |
| ariane133-ng45 | 1003 | 77.74 | -0.28 | -1.71 |
