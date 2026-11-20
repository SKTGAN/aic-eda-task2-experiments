# 第 10 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `368ac3f7f372cbbeef1c9203c1c21453177908b5e051230e51f611f13927e0bb`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **22.14**。

## 模型当时可见的信息

- 事件 69，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 71，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "narrow_gain",
  "improved_cases": 3,
  "regressed_cases": 0,
  "cases": 3,
  "largest_cell": {
    "case": "ariane133-ng45",
    "seed": "1002",
    "score_delta": 58.162757330623215
  },
  "largest_cell_share": 0.798,
  "evidence_candidate_id": "5a8e17d5fdf84831a6be305e9b8d31be549f49f506d85a928c03bd88ec0a1270"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Change vs parent: keep the sampled log-sigmoid contrastive term, and add a net-weight-normalized softplus margin on timing-star graph edges. The edge weights sum to each represented net's fixed timing"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 30.76 | -0.87 | -362.96 |
| bp_fe-ng45 | 1002 | 41.09 | -0.80 | -281.76 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -14.17 | -7.82 | -8615.59 |
| bp-ng45 | 1002 | -28.29 | -7.87 | -10151.86 |
| bp-ng45 | 1003 | -0.74 | -7.92 | -7082.70 |
| ariane133-ng45 | 1001 | 34.58 | -0.27 | -72.21 |
| ariane133-ng45 | 1002 | 53.79 | -0.40 | -26.09 |
| ariane133-ng45 | 1003 | 26.38 | -0.59 | -47.05 |
