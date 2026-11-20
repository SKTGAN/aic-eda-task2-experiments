# 第 1 轮

实际父候选 `57ea753c16a7a4d103c6a77b209d69f8c2659cecc440bd5b76eb4e4ca2643916`。候选 `ebbb7303ecab06df43dc1de37f8dcc733d4ae6837e1e12df2f7a4f6de5cabfe9`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **5.47**。

## 模型当时可见的信息

- 事件 1，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue。
- 事件 3，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

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
  "loss": "Parent loss plus a normalized timing-weighted star-edge attraction term. Change versus parent: keep the random-walk positive/negative objective and add a smooth, timing-weight-normalized penalty on lo"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -20.82 | -8.39 | -9059.34 |
| bp-ng45 | 1002 | -29.97 | -7.84 | -10349.95 |
| bp-ng45 | 1003 | -14.45 | -7.87 | -8622.28 |
| ariane133-ng45 | 1001 | 50.74 | -0.46 | -22.70 |
| ariane133-ng45 | 1002 | -14.13 | -0.68 | -101.27 |
| ariane133-ng45 | 1003 | -56.57 | -0.76 | -159.28 |
