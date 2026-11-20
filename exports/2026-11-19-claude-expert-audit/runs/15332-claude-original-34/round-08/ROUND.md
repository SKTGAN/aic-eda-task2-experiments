# 第 8 轮

实际父候选 `6a8e3ef053a9119bf4daadc0d3bf7f8b8b804d7f0d1e499986ab2f30f4f09edd`。候选 `e9bd095328de9bf0168834f4bb2ef9f817a9ec51af9a312c76332a4be2d746c5`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **22.39**。

## 模型当时可见的信息

没有收录可直接关联本轮提交的模型请求正文。固定 Harness 模板、上一轮回执和计量可单独核对。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "explore_from_incumbent",
  "candidate_id": "6a8e3ef053a9119bf4daadc0d3bf7f8b8b804d7f0d1e499986ab2f30f4f09edd"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Relative to the parent, keep the timing-weighted star-edge attraction term unchanged and add a node-criticality weighting to the contrastive pair term. For each node, a weight in [1, 3] is formed from"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 51.90 | -0.60 | -258.27 |
| bp_fe-ng45 | 1002 | 34.05 | -0.88 | -320.51 |
| bp_fe-ng45 | 1003 | 51.76 | -0.65 | -230.83 |
| bp-ng45 | 1001 | -18.01 | -7.81 | -9045.08 |
| bp-ng45 | 1002 | -57.82 | -7.96 | -13362.81 |
| bp-ng45 | 1003 | -21.57 | -7.80 | -9445.17 |
| ariane133-ng45 | 1001 | 52.73 | -0.33 | -36.09 |
| ariane133-ng45 | 1002 | 43.18 | -0.54 | -25.86 |
| ariane133-ng45 | 1003 | 65.30 | -0.44 | -2.79 |
