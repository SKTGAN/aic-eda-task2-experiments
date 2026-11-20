# 第 4 轮

实际父候选 `08b8f9bd6d7e32cd8393889320eeb5debf0596766599d90efcc74e3b8fd4f741`。候选 `f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **26.93**。

## 模型当时可见的信息

- 事件 30，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "loss",
  "incumbent_id": "08b8f9bd6d7e32cd8393889320eeb5debf0596766599d90efcc74e3b8fd4f741",
  "evidence": {
    "candidate_id": "08b8f9bd6d7e32cd8393889320eeb5debf0596766599d90efcc74e3b8fd4f741",
    "score": 25.345926586583875,
    "parent_id": "057940f3795f03421cbc7c148b8a8c15cdb4ebc0ccc916d543b6e301cd6e5bd3",
    "complete": true,
    "official_score_delta": 2.263660289008044,
    "largest_regression": {
      "case": "bp_fe-ng45",
      "seed": "1002",
      "score_delta": -5.059111964305174,
      "raw_score_contribution_deltas": {
        "wns": -2.6141,
        "tns": -2.445
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "bp_fe-ng45",
      "seed": "1001",
      "score_delta": 18.574932016371267
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 6.790980867024131
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
    "gains_across_seeds": [
      {
        "case": "bp_fe-ng45",
        "improved_seeds": 2,
        "total_seeds": 3,
        "worst_seed_delta": -5.059112
      }
    ],
    "timing_attribution_unconfirmed": [],
    "failures": []
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": {
    "mechanism": "retain the random-walk contrastive loss and the timing-weighted graph-star attraction term, but renormalize graph edges by squared timing weights",
    "decision": "emphasize high-weight timing-critical net-star edges in the embedding gradient while leaving the decoder and all non-graph loss terms unchanged, so the tier decision near decoder b",
    "prediction": "timing-weighted cut should fall and matched-case combined timing should improve across cases and seeds with smaller cross-seed regression than linear edge weighting",
    "falsifier": "matched official combined score fails to improve while decoder assignments and timing-weighted cut remain unchanged."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 47.29 | -0.70 | -258.20 |
| bp_fe-ng45 | 1002 | 44.87 | -0.79 | -240.96 |
| bp_fe-ng45 | 1003 | 62.68 | -0.60 | -128.91 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 83.28 | -0.20 | -2.84 |
| ariane133-ng45 | 1002 | -9.97 | -0.43 | -123.98 |
| ariane133-ng45 | 1003 | 54.36 | -0.45 | -18.18 |
