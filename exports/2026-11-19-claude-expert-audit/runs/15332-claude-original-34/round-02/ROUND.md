# 第 2 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `9fae09f57b95c03259e71450d86f242bd4ff63ba9646d529d0a519e7d1c478c9`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **29.43**。

## 模型当时可见的信息

没有收录可直接关联本轮提交的模型请求正文。固定 Harness 模板、上一轮回执和计量可单独核对。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "opening_control"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Relative to the parent (random-walk contrastive loss only), add a timing-weighted star-edge attraction term sum_e w_e * softplus(-graph_scores_e) / sum_e w_e rescaled by (P+Q)/source_batch_size so its"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 48.11 | -0.68 | -256.68 |
| bp_fe-ng45 | 1002 | 42.05 | -0.77 | -283.38 |
| bp_fe-ng45 | 1003 | 56.09 | -0.60 | -204.56 |
| bp-ng45 | 1001 | -15.37 | -7.83 | -8746.73 |
| bp-ng45 | 1002 | -29.73 | -7.86 | -10313.70 |
| bp-ng45 | 1003 | -1.38 | -7.93 | -7147.70 |
| ariane133-ng45 | 1001 | 35.22 | -0.53 | -39.49 |
| ariane133-ng45 | 1002 | 72.42 | -0.25 | -13.96 |
| ariane133-ng45 | 1003 | 57.44 | -0.45 | -13.74 |
