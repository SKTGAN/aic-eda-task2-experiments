# 第 8 轮

实际父候选 `5470526ceb6dbd551f20e0b2d93013d371e34dc40c5500053aea86b439caa67a`。候选 `ae5c392f7112a729ab33fd9e85c9021a4444247dcac7a2e777711183a546cc0e`。范围 official-runner，账本状态 failed，已取得 9/9 组，完整分 **—**。

## 模型当时可见的信息

- 事件 58，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "no_complete_candidate",
  "component": "decoder",
  "experiment": {
    "id": "X1",
    "kind": "edit",
    "question": "Can a decoder change of S raise bp-ng45 without losing its other designs?"
  },
  "evidence": {
    "candidate_id": "7bd225d180d14732c544e9bcee80f703405dafd8444393e7fb17cbed193c6d8a",
    "score": null,
    "parent_id": "5470526ceb6dbd551f20e0b2d93013d371e34dc40c5500053aea86b439caa67a",
    "complete": false,
    "official_score_delta": null,
    "largest_regression": null,
    "largest_gain": null,
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 0,
        "expected_cells": 3,
        "mean_paired_score_delta": null
      },
      {
        "case": "bp-ng45",
        "scored_pairs": 0,
        "expected_cells": 3,
        "mean_paired_score_delta": null
      },
      {
        "case": "ariane133-ng45",
        "scored_pairs": 0,
        "expected_cells": 3,
        "mean_paired_score_delta": null
      }
    ],
    "gains_across_seeds": [],
    "timing_attribution_unconfirmed": [],
    "failures": [
      {
        "case": "bp_fe-ng45",
        "seed": "1001",
        "failure": {
          "kind": "unclassified",
          "stage": null,
          "component": null,
          "error_type": "ValueError",
          "reason": "[Errno 13] Permission denied: '/root/rolling-3090/official/contest-data/task2/loss_decoder/train/references/bp_fe-ng45/1001/evaluation_result.json'",
          "diagnostics": []
        }
      },
      {
        "case": "bp_fe-ng45",
        "seed": "1002",
        "failure": {
          "kind": "unclassified",
          "stage": null,
          "component": null,
          "error_type": "ValueError",
          "reason": "[Errno 13] Permission denied: '/root/rolling-3090/official/contest-data/task2/loss_decoder/train/references/bp_fe-ng45/1002/evaluation_result.json'",
          "diagnostics": []
        }
      }
    ]
  }
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": {
    "mechanism": "deterministic area-balanced two-anchor Lloyd bisection on L2 embeddings",
    "decision": "nodes above the cumulative-area split along the current area-weighted center-difference axis receive the top die",
    "prediction": "a cleaner antipodal split reduces cross-tier timing-weighted connectivity and raises the bp-ng45 mean paired score versus the parent",
    "falsifier": "bp-ng45 mean paired score does not exceed the parent, or any training case mean falls by more than its 5.0 tolerance."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | — | — | — |
| bp_fe-ng45 | 1002 | — | — | — |
| bp_fe-ng45 | 1003 | — | — | — |
| bp-ng45 | 1001 | — | — | — |
| bp-ng45 | 1002 | — | — | — |
| bp-ng45 | 1003 | — | — | — |
| ariane133-ng45 | 1001 | — | — | — |
| ariane133-ng45 | 1002 | — | — | — |
| ariane133-ng45 | 1003 | — | — | — |
