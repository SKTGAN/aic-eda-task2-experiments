# 第 2 轮

实际父候选 `5f349d8a64df348e8bd59f3918e3a89dbde4f459ef3e0cfbfe097f4a3f43acea`。候选 `7fb5beec1f62e2d35b7e6143215eaacb6c7d1ea0865a478ccf6a42e384deab37`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **14.11**。

## 模型当时可见的信息

- 事件 20，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue。
- 事件 22，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 24，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposals。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "complementary_opening_with_first_receipt",
  "evidence": {
    "candidate_id": "3b05394850e5951fa299e7736ff9904839b57b6e530b81722a89d29d60761329",
    "score": 4.551132504098089,
    "parent_id": "5f349d8a64df348e8bd59f3918e3a89dbde4f459ef3e0cfbfe097f4a3f43acea",
    "complete": true,
    "official_score_delta": -15.873927812163867,
    "largest_regression": {
      "case": "ariane133-ng45",
      "seed": "1002",
      "score_delta": -98.49223961061062,
      "raw_score_contribution_deltas": {
        "wns": -10.059,
        "tns": -211.657
      },
      "score_floor_delta_points": 123.2237
    },
    "largest_gain": {
      "case": "ariane133-ng45",
      "seed": "1001",
      "score_delta": 15.81951185911403
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -1.1944833844808638
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 0.3226618333799583
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -46.74996188539069
      }
    ],
    "gains_across_seeds": [
      {
        "case": "bp-ng45",
        "improved_seeds": 2,
        "total_seeds": 3,
        "worst_seed_delta": -10.20625
      }
    ],
    "timing_attribution_unconfirmed": [
      {
        "case": "ariane133-ng45",
        "seed": "1003",
        "score_delta": -57.577157904675474,
        "wns_slack_delta_ns": 0.07533929249259397,
        "tns_slack_delta_ns": -101.68578444863935
      },
      {
        "case": "bp-ng45",
        "seed": "1003",
        "score_delta": 10.896414077630595,
        "wns_slack_delta_ns": -0.03912958956496926,
        "tns_slack_delta_ns": 1222.6856033712584
      },
      {
        "case": "bp-ng45",
        "seed": "1001",
        "score_delta": 0.2778218030327402,
        "wns_slack_delta_ns": 0.5190967802532169,
        "tns_slack_delta_ns": -233.88657361739206
      }
    ],
    "failures": []
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": {
    "mechanism": "add a timing-weighted margin on star-edge dot products to the maintained contrastive loss",
    "decision": "high-weight star edges receive extra gradient so the unchanged two-means decoder tends to place timing-connected supernodes in one tier",
    "prediction": "timing-weighted cut and combined timing improve versus the parent, especially on bp-ng45",
    "falsifier": "no reduction in timing-weighted cut or nonpositive mean paired combined-score delta across seeds would disprove the hypothesis."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 41.09 | -0.80 | -281.76 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -12.09 | -7.87 | -8362.20 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -2.53 | -7.91 | -7284.26 |
| ariane133-ng45 | 1001 | 43.44 | -0.65 | -12.40 |
| ariane133-ng45 | 1002 | 4.12 | -0.47 | -97.05 |
| ariane133-ng45 | 1003 | -7.06 | -0.75 | -80.58 |
