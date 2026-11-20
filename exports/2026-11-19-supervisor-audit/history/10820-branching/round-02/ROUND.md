# 第 2 轮

实际父候选 `1a194e1aaad116986e5e6ec892ec2d23389d8d44616d54aaebf5b7f34cdd32cc`。候选 `057940f3795f03421cbc7c148b8a8c15cdb4ebc0ccc916d543b6e301cd6e5bd3`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **23.08**。

## 模型当时可见的信息

- 事件 15，用途 详见输入。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, decision_evidence, earlier_edits_from_selected_parent, previous_generation_issue。
- 事件 17，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 19，用途 详见输入。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposals。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "complementary_opening_with_first_receipt",
  "component": "loss",
  "evidence": {
    "candidate_id": "ab93edc407d167411e33901f39e5b79bce15bdbff6371832981b6988474fb27e",
    "score": 12.104234290820933,
    "parent_id": "1a194e1aaad116986e5e6ec892ec2d23389d8d44616d54aaebf5b7f34cdd32cc",
    "complete": true,
    "official_score_delta": -8.320826025441022,
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
      "seed": "1003",
      "score_delta": 39.647566801114955
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -16.17273125573919
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
        "mean_paired_score_delta": -14.34172031679388
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
        "worst_seed_delta": -98.49224
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
  "loss": {
    "mechanism": "retain the random-walk contrastive loss and add a timing-weighted graph-star attraction term over supplied graph edges",
    "decision": "the embedding geometry is pulled toward positive L2 dot products on high-weight net edges, giving timing-critical connected groups a lower cut cost before the frozen area-balanced ",
    "prediction": "matched-case combined timing should improve where timing-weighted cuts are reduced, with labels changing near decoder decision boundaries rather than by case- or seed-specific rule",
    "falsifier": "matched-case combined score fails to improve while timing-weighted cut and decoder assignments remain unchanged."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -20.55 | -7.87 | -9293.23 |
| bp-ng45 | 1002 | -24.49 | -7.88 | -9726.86 |
| bp-ng45 | 1003 | -3.56 | -7.91 | -7399.59 |
| ariane133-ng45 | 1001 | 61.94 | -0.47 | -3.54 |
| ariane133-ng45 | 1002 | -8.28 | -0.53 | -109.75 |
| ariane133-ng45 | 1003 | 68.20 | -0.38 | -4.51 |
