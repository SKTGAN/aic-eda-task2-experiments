# 第 8 轮

实际父候选 `f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd`。候选 `b004e6207435c1340962f8bc821ccab3ef24fa284e0b6b2685053493aba0106b`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **27.50**。

## 模型当时可见的信息

- 事件 47，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "decoder",
  "incumbent_id": "f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd",
  "evidence": {
    "candidate_id": "57c5e845b54c134ab99172798af1d972538b93b179dc3b61dc6318d1f616e297",
    "score": 23.850399484124598,
    "parent_id": "08b8f9bd6d7e32cd8393889320eeb5debf0596766599d90efcc74e3b8fd4f741",
    "complete": true,
    "official_score_delta": -1.4955271024592776,
    "largest_regression": {
      "case": "bp_fe-ng45",
      "seed": "1003",
      "score_delta": -10.355730405894434,
      "raw_score_contribution_deltas": {
        "wns": -1.9191,
        "tns": -8.4366
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "bp_fe-ng45",
      "seed": "1002",
      "score_delta": 4.6167934527223125
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -4.48658130737783
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 0.0
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 0.0
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
    "mechanism": "preserve the frozen seeded area-balanced two-means handoff, then apply only area-corrective bounded wrong-side micro-flips toward the physical-area target",
    "decision": "a group changes tier only when it is closer to the opposite area-weighted center and the move goes from the currently overfull side toward the underfull side, with the same small a",
    "prediction": "timing-weighted cut should remain low while area-balance repair movement and the largest cross-seed regressions shrink, improving matched combined timing over the parent",
    "falsifier": "matched official combined score fails to improve while selected flips are present or area-balance repair movement does not fall."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 47.29 | -0.70 | -258.20 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 62.68 | -0.60 | -128.91 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 83.28 | -0.20 | -2.84 |
| ariane133-ng45 | 1002 | -9.97 | -0.43 | -123.98 |
| ariane133-ng45 | 1003 | 54.36 | -0.45 | -18.18 |
