# 第 5 轮

实际父候选 `f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd`。候选 `fa9b732e2e9f7e80eb3d299e0c08fe811379003a0a8395540c73512e9e28a729`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **24.67**。

## 模型当时可见的信息

- 事件 35，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "decoder",
  "incumbent_id": "f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd",
  "evidence": {
    "candidate_id": "f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd",
    "score": 26.934765853528955,
    "parent_id": "08b8f9bd6d7e32cd8393889320eeb5debf0596766599d90efcc74e3b8fd4f741",
    "complete": true,
    "official_score_delta": 1.5888392669450795,
    "largest_regression": {
      "case": "ariane133-ng45",
      "seed": "1003",
      "score_delta": -13.835096064999043,
      "raw_score_contribution_deltas": {
        "wns": -5.3251,
        "tns": -8.51
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "ariane133-ng45",
      "seed": "1001",
      "score_delta": 21.335924804760744
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 0.0
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 2.8291972476403235
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 1.9373205531949107
      }
    ],
    "gains_across_seeds": [],
    "timing_attribution_unconfirmed": [],
    "failures": []
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": {
    "mechanism": "preserve the frozen seeded area-balanced two-means handoff and replace the parent's one-sided high-margin micro-flip with a two-sided balanced swap of groups that are closer to the",
    "decision": "change a group's tier only when a wrong-side group on the opposite tier of comparable cumulative area is also moved, so the local swap does not shift the global area balance or cen",
    "prediction": "the largest one-sided-drift regressions should shrink while the boundary gains persist, giving higher mean combined timing across seeds and a lower timing-weighted cut",
    "falsifier": "matched official combined score fails to improve over the parent while the selected swaps are absent or the timing-weighted cut rises."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 83.28 | -0.20 | -2.84 |
| ariane133-ng45 | 1002 | -9.97 | -0.43 | -123.98 |
| ariane133-ng45 | 1003 | 54.36 | -0.45 | -18.18 |
