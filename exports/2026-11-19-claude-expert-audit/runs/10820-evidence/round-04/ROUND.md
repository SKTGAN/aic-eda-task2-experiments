# 第 4 轮

实际父候选 `bd829199bc51a4e13005b84d9699f7851a81defca1674d458f910deae617800a`。候选 `4a5ff3c1c45b1cd1a5563ee17284b8e3a9d70b07bf9dbbc6d97a61e5e09301e5`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **25.01**。

## 模型当时可见的信息

- 事件 35，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "concentrated_regression",
  "largest_regression": {
    "case": "bp_fe-ng45",
    "seed": "1001",
    "score_delta": -33.00992456232483,
    "raw_score_contribution_deltas": {
      "wns": -15.6295,
      "tns": -17.3804
    },
    "score_floor_delta_points": 0.0
  },
  "component": "loss",
  "evidence": {
    "candidate_id": "bd829199bc51a4e13005b84d9699f7851a81defca1674d458f910deae617800a",
    "score": 26.48940508129844,
    "parent_id": "5f349d8a64df348e8bd59f3918e3a89dbde4f459ef3e0cfbfe097f4a3f43acea",
    "complete": true,
    "official_score_delta": 6.064344765036484,
    "largest_regression": {
      "case": "bp_fe-ng45",
      "seed": "1001",
      "score_delta": -33.00992456232483,
      "raw_score_contribution_deltas": {
        "wns": -15.6295,
        "tns": -17.3804
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "ariane133-ng45",
      "seed": "1002",
      "score_delta": 42.00279086272267
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -9.330351180450757
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 8.393191589377082
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 19.13019388618313
      }
    ],
    "gains_across_seeds": [
      {
        "case": "bp-ng45",
        "improved_seeds": 3,
        "total_seeds": 3,
        "worst_seed_delta": 5.481685
      },
      {
        "case": "ariane133-ng45",
        "improved_seeds": 2,
        "total_seeds": 3,
        "worst_seed_delta": -1.303223
      }
    ],
    "timing_attribution_unconfirmed": [
      {
        "case": "bp-ng45",
        "seed": "1002",
        "score_delta": 5.481684607966681,
        "wns_slack_delta_ns": -0.03535216663915186,
        "tns_slack_delta_ns": 623.0839238702301
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
    "mechanism": "retain timing-coverage and normalized slack-severity positive-pair weighting, but halve its amplitude to limit over-attraction from the most severe endpoint groups",
    "decision": "high-severity connected groups still receive stronger embedding attraction, yet the maximum extra positive weight is reduced relative to the parent loss",
    "prediction": "the bp_fe-ng45 seed 1001 regression narrows while the bp-ng45 and ariane133 gains largely persist, and timing-weighted cut remains below the unweighted baseline",
    "falsifier": "a smaller mean paired combined-score delta than the parent across the training cells, or no reduction in the largest bp_fe-ng45 seed 1001 regression, would disprove the hypothesis."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 39.41 | -0.84 | -275.88 |
| bp_fe-ng45 | 1002 | 57.15 | -0.65 | -167.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -12.06 | -7.87 | -8358.31 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -6.18 | -7.93 | -7679.81 |
| ariane133-ng45 | 1001 | 67.67 | -0.39 | -4.48 |
| ariane133-ng45 | 1002 | 23.64 | -0.31 | -84.67 |
| ariane133-ng45 | 1003 | 24.10 | -0.69 | -37.60 |
