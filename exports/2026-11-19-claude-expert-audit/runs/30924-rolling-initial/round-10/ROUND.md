# 第 10 轮

实际父候选 `5470526ceb6dbd551f20e0b2d93013d371e34dc40c5500053aea86b439caa67a`。候选 `5de872959cabee13e1f18973f290f1b357fd8b38a4064aedfe8987696f2d288d`。范围 official-runner，账本状态 failed，已取得 9/9 组，完整分 **—**。

## 模型当时可见的信息

- 事件 73，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。
- 事件 76，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。
- 事件 79，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。

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
    "candidate_id": "c0771e086e41985e24352c7c69fe3375931e53949a44b36998ec2749a9c66f34",
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
    "mechanism": "center L2 embeddings, initialize the split axis at the physical-area-weighted maximum-variance coordinate, then alternate an area-cumulative projection split with area-weighted cen",
    "decision": "each iteration assigns whole supernodes to the top tier when their projection lies above the cumulative-area balance cut, changing the discrete partition rather than any loss term",
    "prediction": "a cleaner global separation of graph-similar groups should reduce cross-tier timing-weighted connectivity and raise the mean bp-ng45 paired score versus the frozen reference decode",
    "falsifier": "if the mean bp-ng45 paired score does not exceed the parent or any training case mean falls by more than 5 points, the mechanism is rejected."
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
