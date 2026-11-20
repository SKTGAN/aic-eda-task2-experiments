# 第 5 轮

实际父候选 `57ea753c16a7a4d103c6a77b209d69f8c2659cecc440bd5b76eb4e4ca2643916`。候选 `9dac911dd21d088b013179c2902908eccf4876c5d315b2d3fc564a2f578a3d85`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **2.79**。

## 模型当时可见的信息

- 事件 30，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 32，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "28ff7be4a61e14eeced2663d68fb9a712d05028f7ddcbc840d1cf367485209fe",
  "reason": "orientation_only",
  "identical_assignments": 1,
  "kept_up_to_swap": 5,
  "die_swaps": 6
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Parent random-walk contrastive loss plus criticality geometry alignment. Change versus parent: keep the maintained positive/negative objective and add a masked, standardized worst-slack alignment pena"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 45.59 | -0.62 | -321.78 |
| bp_fe-ng45 | 1002 | 44.60 | -0.81 | -233.29 |
| bp_fe-ng45 | 1003 | 24.98 | -0.70 | -527.27 |
| bp-ng45 | 1001 | -15.50 | -8.00 | -8669.77 |
| bp-ng45 | 1002 | -100.00 | — | — |
| bp-ng45 | 1003 | -19.98 | -7.93 | -9202.44 |
| ariane133-ng45 | 1001 | -100.00 | -0.68 | -257.52 |
| ariane133-ng45 | 1002 | 84.60 | -0.20 | -0.94 |
| ariane133-ng45 | 1003 | 60.86 | -0.44 | -9.18 |
