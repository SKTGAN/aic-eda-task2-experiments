# 第 7 轮

实际父候选 `1419acdef89f42cf77febf4669e8a8f48665755853884d7ee31b30de8888d09a`。候选 `f4a8bad252ad2e09289347c6583bfb0ecee9eb39c56b340e35d3b5ee00d1fb11`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **-100.00**。

## 模型当时可见的信息

- 事件 45，用途 plan。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, recent_feedback, prior_trials, related_experiment, previous_generation_issue, start_reference。
- 事件 47，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, previous_generation_issue, experiment_plan, prior_trials, largest_regression。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "candidate_id": "a498b035c2cde27d0203ebf4bae6d76bf5c60cce80b3da86dbd41ef19ab8723d",
  "reason": "narrow_gain",
  "improved_cases": 2,
  "regressed_cases": 1,
  "cases": 3,
  "largest_cell": {
    "case": "ariane133-ng45",
    "seed": "1001",
    "score_delta": 82.68097595380047
  },
  "largest_cell_share": 1.245
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Area-balanced principal-axis split instead of seeded area-weighted two-means. Relative to the parent reference decoder, this uses deterministic power iteration on the area-weighted centered embedding "
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | -100.00 | — | — |
| bp_fe-ng45 | 1002 | -100.00 | — | — |
| bp_fe-ng45 | 1003 | -100.00 | — | — |
| bp-ng45 | 1001 | -100.00 | — | — |
| bp-ng45 | 1002 | -100.00 | — | — |
| bp-ng45 | 1003 | -100.00 | — | — |
| ariane133-ng45 | 1001 | -100.00 | — | — |
| ariane133-ng45 | 1002 | -100.00 | — | — |
| ariane133-ng45 | 1003 | -100.00 | — | — |
