# 第 3 轮

实际父候选 `5f349d8a64df348e8bd59f3918e3a89dbde4f459ef3e0cfbfe097f4a3f43acea`。候选 `bd829199bc51a4e13005b84d9699f7851a81defca1674d458f910deae617800a`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **26.49**。

## 模型当时可见的信息

- 事件 30，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "published_start_still_ahead",
  "evidence": {
    "candidate_id": "7fb5beec1f62e2d35b7e6143215eaacb6c7d1ea0865a478ccf6a42e384deab37",
    "score": 14.11487288013456,
    "parent_id": "5f349d8a64df348e8bd59f3918e3a89dbde4f459ef3e0cfbfe097f4a3f43acea",
    "complete": true,
    "official_score_delta": -6.310187436127395,
    "largest_regression": {
      "case": "ariane133-ng45",
      "seed": "1003",
      "score_delta": -45.15039897002015,
      "raw_score_contribution_deltas": {
        "wns": -13.5355,
        "tns": -31.6149
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "bp-ng45",
      "seed": "1003",
      "score_delta": 11.928014112747784
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -12.040558437106787
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 8.715644188753684
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -15.605648060029083
      }
    ],
    "gains_across_seeds": [
      {
        "case": "bp-ng45",
        "improved_seeds": 3,
        "total_seeds": 3,
        "worst_seed_delta": 5.481685
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
    "mechanism": "weight sampled positive pairs by timing-coverage and normalized slack severity of their endpoint supernodes while leaving negatives unchanged",
    "decision": "high-severity connected groups receive stronger embedding attraction so the unchanged area-balanced two-means decoder can place them in one tier",
    "prediction": "timing-weighted cut and TNS improve more than WNS versus the parent, with less collateral regression than the graph-margin trial on ariane133 seed 1003",
    "falsifier": "a nonpositive mean paired combined-score delta across the training cells or no reduction in timing-weighted cut on high-severity pairs would disprove the hypothesis."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 22.99 | -1.01 | -382.39 |
| bp_fe-ng45 | 1002 | 57.39 | -0.62 | -177.94 |
| bp_fe-ng45 | 1003 | 53.39 | -0.64 | -218.28 |
| bp-ng45 | 1001 | -13.05 | -7.83 | -8486.02 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -2.53 | -7.91 | -7284.26 |
| ariane133-ng45 | 1001 | 49.43 | -0.43 | -28.49 |
| ariane133-ng45 | 1002 | 40.50 | -0.38 | -49.87 |
| ariane133-ng45 | 1003 | 54.78 | -0.47 | -16.03 |
