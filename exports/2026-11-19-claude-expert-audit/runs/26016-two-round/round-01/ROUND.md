# 第 1 轮

实际父候选 `61f3b185325fbca423a8fda18251b00c51c597eb38009c8d91681bbaed8427ba`。候选 `35f0adc0cba637fe1c74f640d79be37048934097920bbb0bb2b9fa95e65d3934`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **17.60**。

## 模型当时可见的信息

- 事件 1，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。
- 事件 4，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。
- 事件 6，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 9，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 12，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposals。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "opening_control",
  "component": "loss"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": {
    "mechanism": "add a normalized timing-weighted star-edge attraction (1 - graph_scores) to the unchanged random-walk logsigmoid pair loss",
    "decision": "each connected net star contributes graph_weights-normalized attraction, changing embeddings but not the decoder",
    "prediction": "critical connected supernodes should co-locate, lowering timing-weighted cut and improving TNS after feasible partitioning",
    "falsifier": "if matched cells show no lower timing-weighted cut or TNS worsens, the graph-attraction hypothesis is disproved."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 50.56 | -0.66 | -242.39 |
| bp_fe-ng45 | 1002 | 54.62 | -0.74 | -150.06 |
| bp_fe-ng45 | 1003 | 53.13 | -0.66 | -207.79 |
| bp-ng45 | 1001 | -25.36 | -7.87 | -9828.26 |
| bp-ng45 | 1002 | -29.85 | -7.82 | -10347.17 |
| bp-ng45 | 1003 | -6.25 | -7.86 | -7724.03 |
| ariane133-ng45 | 1001 | 65.63 | -0.40 | -6.37 |
| ariane133-ng45 | 1002 | -37.93 | -0.49 | -162.63 |
| ariane133-ng45 | 1003 | 33.83 | -0.71 | -20.66 |
