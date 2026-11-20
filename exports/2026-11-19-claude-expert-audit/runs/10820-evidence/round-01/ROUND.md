# 第 1 轮

实际父候选 `5f349d8a64df348e8bd59f3918e3a89dbde4f459ef3e0cfbfe097f4a3f43acea`。候选 `3b05394850e5951fa299e7736ff9904839b57b6e530b81722a89d29d60761329`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **4.55**。

## 模型当时可见的信息

- 事件 1，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue。
- 事件 4，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue。
- 事件 7，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue。
- 事件 10，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue。
- 事件 12，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 14，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposals。

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
  "decoder": {
    "mechanism": "seeded area-weighted two-means with deterministic farthest anchors and a cumulative-area cut",
    "decision": "each node's tier follows the nearer area-balanced center after ranking by squared-distance margin",
    "prediction": "tighter embedding-coherent balanced groups reduce timing-weighted cut and improve combined timing",
    "falsifier": "unchanged final weighted cut or nonpositive paired combined score across the training cells would disprove the mechanism."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 45.64 | -0.63 | -314.46 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 62.60 | -0.60 | -126.69 |
| bp-ng45 | 1001 | -20.55 | -7.87 | -9293.23 |
| bp-ng45 | 1002 | -40.18 | -7.89 | -11449.92 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 66.56 | -0.30 | -16.82 |
| ariane133-ng45 | 1002 | -100.00 | -0.64 | -441.15 |
| ariane133-ng45 | 1003 | -19.49 | -0.50 | -131.45 |
