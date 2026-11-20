# 第 4 轮

实际父候选 `1158d4c5d9ab996a249ea70f3943a9effc42bb871010750a20a2b20c42a8e877`。候选 `c12ba8689ce44c0cffa39b6372fd7328a33d9480557ab2febbd8faf4eff9cf20`。范围 official-runner，账本状态 failed，已取得 6/9 组，完整分 **—**。

## 模型当时可见的信息

- 事件 41，用途 generation。可读输入字段 search_intent, decision, parent_id, parent_program, training_cells, evaluations_remaining, parent_feedback, incumbent_feedback, last_trial, prior_trials, related_experiment, previous_generation_issue, experiment。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "extend_best",
  "component": "loss",
  "incumbent_id": "1158d4c5d9ab996a249ea70f3943a9effc42bb871010750a20a2b20c42a8e877",
  "experiment": {
    "id": "X1",
    "kind": "edit",
    "question": "Can a loss change of R1 raise bp_fe-ng45 without losing its other designs?"
  },
  "evidence": {
    "candidate_id": "fbe23720f8a5f3ed055048e2f6a8a2ab87917806e53e704a198bddc35a803ccf",
    "score": -9.327544750469832,
    "parent_id": "1158d4c5d9ab996a249ea70f3943a9effc42bb871010750a20a2b20c42a8e877",
    "complete": true,
    "official_score_delta": -32.74731323292649,
    "largest_regression": {
      "case": "ariane133-ng45",
      "seed": "1003",
      "score_delta": -182.90347288189028
    },
    "largest_gain": null,
    "paired_case_deltas": [
      {
        "case": "bp_fe-ng45",
        "scored_pairs": 3,
        "expected_cells": 3,
        "mean_paired_score_delta": -4.443368867945812
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
        "mean_paired_score_delta": -93.79857083083364
      }
    ],
    "gains_across_seeds": [],
    "timing_attribution_unconfirmed": [],
    "failures": [
      {
        "case": "ariane133-ng45",
        "seed": "1002",
        "failure": {
          "kind": "physical_penalty",
          "stage": "30_placement",
          "component": null,
          "error_type": null,
          "reason": "placement: command failed with code 1; see /root/rolling-3090/feedback/work-v2/evaluations/e-5b21d43b166492c295416df75e9710c0e956498974484888d903f902958d/cells/ariane133-ng45/1002/result/run/30_placement/run.log",
          "diagnostics": []
        }
      },
      {
        "case": "ariane133-ng45",
        "seed": "1003",
        "failure": {
          "kind": "physical_penalty",
          "stage": "30_placement",
          "component": null,
          "error_type": null,
          "reason": "placement: command failed with code 1; see /root/rolling-3090/feedback/work-v2/evaluations/e-5b21d43b166492c295416df75e9710c0e956498974484888d903f902958d/cells/ariane133-ng45/1003/result/run/30_placement/run.log",
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
  "loss": {
    "mechanism": "add an angular-margin correction to the maintained random-walk pair objective",
    "decision": "raise loss when positive dot products fall below a margin and when sampled negative dot products exceed a negative margin",
    "prediction": "the sharper pair geometry changes the embedding partition and raises the target case's mean paired score while other case means stay within the stated tolerance",
    "falsifier": "target-case mean paired delta is non-positive against the parent, or any non-target case mean falls more than 5 points below the parent."
  }
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1003 | -15.86 | -0.72 | -222.70 |
| bp_fe-ng45 | 1002 | -32.69 | -0.83 | -307.95 |
| bp_fe-ng45 | 1001 | 9.28 | -0.57 | -164.06 |
| bp-ng45 | 1003 | 3.59 | -7.92 | -8068.13 |
| bp-ng45 | 1002 | -18.96 | -7.82 | -13641.91 |
| bp-ng45 | 1001 | 7.08 | -7.96 | -8299.61 |
