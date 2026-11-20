# 第 3 轮

实际父候选 `057940f3795f03421cbc7c148b8a8c15cdb4ebc0ccc916d543b6e301cd6e5bd3`。候选 `08b8f9bd6d7e32cd8393889320eeb5debf0596766599d90efcc74e3b8fd4f741`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **25.35**。

## 模型当时可见的信息

- 事件 25，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "decoder",
  "incumbent_id": "057940f3795f03421cbc7c148b8a8c15cdb4ebc0ccc916d543b6e301cd6e5bd3",
  "evidence": {
    "candidate_id": "057940f3795f03421cbc7c148b8a8c15cdb4ebc0ccc916d543b6e301cd6e5bd3",
    "score": 23.08226629757583,
    "parent_id": "1a194e1aaad116986e5e6ec892ec2d23389d8d44616d54aaebf5b7f34cdd32cc",
    "complete": true,
    "official_score_delta": 2.6572059813138758,
    "largest_regression": {
      "case": "bp_fe-ng45",
      "seed": "1001",
      "score_delta": -27.284925266225567,
      "raw_score_contribution_deltas": {
        "wns": -14.7623,
        "tns": -12.5226
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "ariane133-ng45",
      "seed": "1003",
      "score_delta": 30.10895203046754
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -9.094975088741856
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 5.551973496210006
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 11.51461953647348
      }
    ],
    "gains_across_seeds": [
      {
        "case": "bp-ng45",
        "improved_seeds": 3,
        "total_seeds": 3,
        "worst_seed_delta": 0.277822
      },
      {
        "case": "ariane133-ng45",
        "improved_seeds": 2,
        "total_seeds": 3,
        "worst_seed_delta": -6.768624
      }
    ],
    "timing_attribution_unconfirmed": [
      {
        "case": "bp-ng45",
        "seed": "1003",
        "score_delta": 10.896414077630595,
        "wns_slack_delta_ns": -0.03912958956496926,
        "tns_slack_delta_ns": 1222.6856033712584
      },
      {
        "case": "bp-ng45",
        "seed": "1002",
        "score_delta": 5.481684607966681,
        "wns_slack_delta_ns": -0.03535216663915186,
        "tns_slack_delta_ns": 623.0839238702301
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
  "decoder": {
    "mechanism": "preserve the frozen seeded area-balanced two-means handoff, then apply a bounded deterministic local reassignment of groups that are closer to the opposite area-weighted center",
    "decision": "flip only a small area- and count-capped set of high-margin wrong-side groups, preserving the reference global orientation and macro-feasibility neighborhood",
    "prediction": "timing-weighted cut and combined score should improve where reference area rounding left boundary groups on the wrong side, without the large swings caused by global label flips",
    "falsifier": "matched-case combined score fails to improve while the selected flips are absent or the timing-weighted cut does not fall."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 47.29 | -0.70 | -258.20 |
| bp_fe-ng45 | 1002 | 44.87 | -0.79 | -240.96 |
| bp_fe-ng45 | 1003 | 62.68 | -0.60 | -128.91 |
| bp-ng45 | 1001 | -20.55 | -7.87 | -9293.23 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 61.94 | -0.47 | -3.54 |
| ariane133-ng45 | 1002 | -8.28 | -0.53 | -109.75 |
| ariane133-ng45 | 1003 | 68.20 | -0.38 | -4.51 |
