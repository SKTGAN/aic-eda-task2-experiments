# 第 2 轮

实际父候选 `ce56a2d8d7961bd45378b9d44dd3dcce30148d115c8f26bc614ecf9cb4ac4570`。候选 `57e8cc549349c019fd93e27bf502aa1eb5cae0c814cdf2a34e1e6c19833399f2`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **18.22**。

## 模型当时可见的信息

- 事件 15，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, related_experiment, previous_generation_issue。
- 事件 17，用途 详见输入。可读输入字段 search_intent, parent_program, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 19，用途 详见输入。可读输入字段 search_intent, parent_program, official_interface, proposals。

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
  "loss": "Parent random-walk pair objective with timing/area pair reweighting. Mechanism: keep the parent logistic positive/negative pair geometry, but weight each sampled pair by endpoint timing-criticality an"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 46.76 | -0.61 | -314.93 |
| bp_fe-ng45 | 1002 | 35.40 | -0.88 | -303.92 |
| bp_fe-ng45 | 1003 | 53.71 | -0.64 | -214.54 |
| bp-ng45 | 1001 | -27.27 | -7.91 | -10015.50 |
| bp-ng45 | 1002 | -28.80 | -7.88 | -10199.93 |
| bp-ng45 | 1003 | -5.54 | -7.88 | -7635.98 |
| ariane133-ng45 | 1001 | 24.55 | -0.77 | -27.79 |
| ariane133-ng45 | 1002 | -5.33 | -0.27 | -136.31 |
| ariane133-ng45 | 1003 | 70.47 | -0.37 | -2.78 |
