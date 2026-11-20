# 第 10 轮

实际父候选 `b004e6207435c1340962f8bc821ccab3ef24fa284e0b6b2685053493aba0106b`。候选 `c7efc28d8d82401042c94c0af19b47960524f0a12836a61766f25b8116ff4c33`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **23.23**。

## 模型当时可见的信息

- 事件 56，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "decoder",
  "incumbent_id": "b004e6207435c1340962f8bc821ccab3ef24fa284e0b6b2685053493aba0106b",
  "evidence": {
    "candidate_id": "7e9f2c22f0b9a2c0e9942ff83606218e0bb03db16a50c8b9a3dbbe76b1899e37",
    "score": 7.186323862832915,
    "parent_id": "b004e6207435c1340962f8bc821ccab3ef24fa284e0b6b2685053493aba0106b",
    "complete": true,
    "official_score_delta": -20.310565542285502,
    "largest_regression": {
      "case": "ariane133-ng45",
      "seed": "1003",
      "score_delta": -154.36461988789705,
      "raw_score_contribution_deltas": {
        "wns": -35.332,
        "tns": -124.3548
      },
      "score_floor_delta_points": 5.3222
    },
    "largest_gain": {
      "case": "ariane133-ng45",
      "seed": "1002",
      "score_delta": 7.350342736597421
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
        "mean_paired_score_delta": -0.5866850616446927
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -60.34501156521181
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
    "mechanism": "preserve the frozen seeded area-balanced two-means handoff, then apply two bounded area-corrective wrong-side micro-flip passes with recentered area-weighted centers after the firs",
    "decision": "a group changes tier on each pass only when it is closer to the opposite recentered center and the move goes from the currently overfull side toward the underfull side, with a smal",
    "prediction": "timing-weighted cut should fall further and matched combined timing should improve across more cases and seeds than the single-pass parent while preserving its prior gain",
    "falsifier": "matched official combined score fails to improve over the parent while second-pass selected flips are present or timing-weighted cut does not fall."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 14.95 | -1.11 | -425.27 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 56.63 | -0.65 | -173.00 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 83.28 | -0.20 | -2.84 |
| ariane133-ng45 | 1002 | -9.97 | -0.43 | -123.98 |
| ariane133-ng45 | 1003 | 54.36 | -0.45 | -18.18 |
