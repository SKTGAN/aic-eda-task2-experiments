# 第 4 轮

实际父候选 `1419acdef89f42cf77febf4669e8a8f48665755853884d7ee31b30de8888d09a`。候选 `241b7a65be7e80e7e15109af6cfb85b852c49f9f3cd110ade249ac6c2ff9967a`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **11.79**。

## 模型当时可见的信息

- 事件 27，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 29，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "5b979eeb4cf4c9f649ec055bd9e35c2d11109f2ad57b507505612e81baa6e2d2",
  "reason": "narrow_gain",
  "improved_cases": 1,
  "regressed_cases": 2,
  "cases": 3,
  "largest_cell": {
    "case": "ariane133-ng45",
    "seed": "1001",
    "score_delta": 89.21369156710341
  },
  "largest_cell_share": 1.273
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Replace the parent decoder with one bounded area-weighted two-means loop whose final split uses a deterministic affinity-margin ordering plus cumulative physical area rather than nearest-center roundi"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 36.53 | -0.87 | -297.42 |
| bp_fe-ng45 | 1002 | 34.25 | -0.88 | -317.16 |
| bp_fe-ng45 | 1003 | 62.60 | -0.60 | -126.69 |
| bp-ng45 | 1001 | -13.26 | -7.92 | -8466.77 |
| bp-ng45 | 1002 | -40.18 | -7.89 | -11449.92 |
| bp-ng45 | 1003 | -4.59 | -7.88 | -7530.42 |
| ariane133-ng45 | 1001 | -22.66 | -1.01 | -74.58 |
| ariane133-ng45 | 1002 | -24.34 | -0.55 | -132.46 |
| ariane133-ng45 | 1003 | 77.74 | -0.28 | -1.71 |
