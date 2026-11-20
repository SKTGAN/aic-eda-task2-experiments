# 第 4 轮

实际父候选 `57ea753c16a7a4d103c6a77b209d69f8c2659cecc440bd5b76eb4e4ca2643916`。候选 `28ff7be4a61e14eeced2663d68fb9a712d05028f7ddcbc840d1cf367485209fe`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **15.61**。

## 模型当时可见的信息

- 事件 24，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 26，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "7b2b7f4fc3cf05ce63fb33e044e4551f7842955c5e6d25de18f63280f83a9b2d",
  "reason": "narrow_gain",
  "improved_cases": 1,
  "regressed_cases": 2,
  "cases": 3,
  "largest_cell": {
    "case": "ariane133-ng45",
    "seed": "1002",
    "score_delta": 89.94374755362402
  },
  "largest_cell_share": 3.373
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Decode on mean-removed embedding geometry with a balanced margin sweep. Change versus the parent program: the parent delegates the whole design split to ``reference_global_two_way`` (raw L2-normalized"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 41.85 | -0.83 | -253.64 |
| bp_fe-ng45 | 1002 | 30.71 | -0.88 | -358.36 |
| bp_fe-ng45 | 1003 | 54.90 | -0.68 | -178.68 |
| bp-ng45 | 1001 | -10.22 | -8.16 | -8007.85 |
| bp-ng45 | 1002 | -51.95 | -7.83 | -12781.88 |
| bp-ng45 | 1003 | -9.63 | -8.21 | -7918.39 |
| ariane133-ng45 | 1001 | 50.74 | -0.46 | -22.70 |
| ariane133-ng45 | 1002 | 17.26 | -0.49 | -72.84 |
| ariane133-ng45 | 1003 | 16.80 | -0.60 | -61.06 |
