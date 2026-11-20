# 第 2 轮

实际父候选 `5470526ceb6dbd551f20e0b2d93013d371e34dc40c5500053aea86b439caa67a`。候选 `8f2d565aa91c9f82047e47f5427c7ea71300b34822f1fc8240f3436de74a2229`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **-1.89**。

## 模型当时可见的信息

- 事件 22，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。
- 事件 24，用途 generation。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposal_a, proposal_a_added_signals, previous_alternative_issue。
- 事件 26，用途 generation。可读输入字段 search_intent, parent_program, evidence_brief, official_interface, proposals。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "complementary_opening_with_first_receipt",
  "component": "loss",
  "experiment": {
    "id": "X1",
    "kind": "edit",
    "question": "Can a loss change of S raise bp-ng45 without losing its other designs?"
  },
  "evidence": {
    "candidate_id": "1158d4c5d9ab996a249ea70f3943a9effc42bb871010750a20a2b20c42a8e877",
    "score": 23.419768482456654,
    "parent_id": "5470526ceb6dbd551f20e0b2d93013d371e34dc40c5500053aea86b439caa67a",
    "complete": true,
    "official_score_delta": 2.994708166194698,
    "largest_regression": {
      "case": "bp-ng45",
      "seed": "1002",
      "score_delta": -21.980947240618118,
      "raw_score_contribution_deltas": {
        "wns": 0.0515,
        "tns": -22.0324
      },
      "score_floor_delta_points": 0.0
    },
    "largest_gain": {
      "case": "ariane133-ng45",
      "seed": "1003",
      "score_delta": 44.81270895946172
    },
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -3.770752816100893
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -2.182692338468929
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": 14.937569653153908
      }
    ],
    "gains_across_seeds": [
      {
        "case": "bp-ng45",
        "improved_seeds": 2,
        "total_seeds": 3,
        "worst_seed_delta": -21.980947
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
    "mechanism": "add a timing-weight-normalized star-edge attraction term to the maintained pair objective",
    "decision": "raise the loss when high-weight graph-connected supernode embeddings are dissimilar, pushing them toward the same unchanged decoder tier",
    "prediction": "the target case's mean paired score rises with a less-negative TNS deficit while other case means stay within tolerance",
    "falsifier": "target-case mean paired score delta is non-positive, or any case mean falls more than 5 points below the parent."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 28.72 | -0.99 | -324.35 |
| bp_fe-ng45 | 1002 | 49.93 | -0.73 | -211.75 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -20.82 | -8.39 | -9059.34 |
| bp-ng45 | 1002 | -29.97 | -7.84 | -10349.95 |
| bp-ng45 | 1003 | -6.98 | -7.96 | -7750.49 |
| ariane133-ng45 | 1001 | -56.97 | -0.42 | -200.74 |
| ariane133-ng45 | 1002 | 19.81 | -0.47 | -71.42 |
| ariane133-ng45 | 1003 | -56.57 | -0.76 | -159.28 |
