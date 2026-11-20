# 第 1 轮

实际父候选 `ce56a2d8d7961bd45378b9d44dd3dcce30148d115c8f26bc614ecf9cb4ac4570`。候选 `a8cd13efbc3cb709ae662ecade4f0eb69a221036995aab9079a3151ab3f5aae3`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **5.48**。

## 模型当时可见的信息

- 事件 1，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。
- 事件 3，用途 详见输入。可读输入字段 search_intent, parent_program, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 6，用途 详见输入。可读输入字段 search_intent, parent_program, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 9，用途 详见输入。可读输入字段 search_intent, parent_program, official_interface, proposals。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "opening_control"
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Parent delegates to reference_global_two_way. This version changes the decoder to a deterministic area-balanced embedding sweep refined by bounded capacity-constrained Lloyd updates: each step ranks n"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 45.64 | -0.63 | -314.46 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 62.60 | -0.60 | -126.69 |
| bp-ng45 | 1001 | -13.26 | -7.92 | -8466.77 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -4.59 | -7.88 | -7530.42 |
| ariane133-ng45 | 1001 | -22.66 | -1.01 | -74.58 |
| ariane133-ng45 | 1002 | -24.34 | -0.55 | -132.46 |
| ariane133-ng45 | 1003 | -19.49 | -0.50 | -131.45 |
