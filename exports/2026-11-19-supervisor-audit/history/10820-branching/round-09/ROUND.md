# 第 9 轮

实际父候选 `b004e6207435c1340962f8bc821ccab3ef24fa284e0b6b2685053493aba0106b`。候选 `7e9f2c22f0b9a2c0e9942ff83606218e0bb03db16a50c8b9a3dbbe76b1899e37`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **7.19**。

## 模型当时可见的信息

- 事件 52，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "loss",
  "incumbent_id": "b004e6207435c1340962f8bc821ccab3ef24fa284e0b6b2685053493aba0106b",
  "evidence": {
    "candidate_id": "b004e6207435c1340962f8bc821ccab3ef24fa284e0b6b2685053493aba0106b",
    "score": 27.496889405118417,
    "parent_id": "f58f249ecbf580fd2626d25b63a539ea2beec5601b4f8655a0f4474ac51bdddd",
    "complete": true,
    "official_score_delta": 0.5621235515894618,
    "largest_regression": null,
    "largest_gain": {
      "case": "bp_fe-ng45",
      "seed": "1002",
      "score_delta": 5.059111964305174
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 1.6863706547683914
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
  "loss": {
    "mechanism": "retain the random-walk contrastive pair loss and the timing-weighted graph-star attraction term, but sharpen graph-edge weights to the cubic power of the supplied timing weights",
    "decision": "superlinearly emphasize the highest-weight timing-critical net-star edges in the embedding gradient while leaving the pair loss, graph normalization, graph coefficient, and decoder",
    "prediction": "timing-weighted cut should fall and matched official combined timing should improve across cases and seeds, especially where moderate-weight attraction previously diluted the most ",
    "falsifier": "matched official combined score fails to improve while decoder assignments and timing-weighted cut remain unchanged."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 47.29 | -0.70 | -258.20 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 62.68 | -0.60 | -128.91 |
| bp-ng45 | 1001 | -13.82 | -7.87 | -8552.39 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 49.26 | -0.34 | -39.94 |
| ariane133-ng45 | 1002 | -2.61 | -0.48 | -106.99 |
| ariane133-ng45 | 1003 | -100.00 | -0.92 | -218.03 |
