# 第 1 轮

实际父候选 `c936085bfae4a448ff978d007b0f1a66c623b4d761a4a6a32683bb214d6e96b7`。候选 `2c6175c2467c571df6d2a1d20150c1df6a0e47b2f9466cc4c9c52ee71c49b1e2`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **11.94**。

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
  "decoder": "Replace the frozen two-means decoder with an area-balanced principal-axis split. Relative to the parent, this keeps the same legal area-balanced top-die fill but ranks groups by a power-iteration proj"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 38.47 | -0.90 | -255.98 |
| bp_fe-ng45 | 1002 | 46.61 | -0.72 | -257.91 |
| bp_fe-ng45 | 1003 | 49.71 | -0.63 | -268.23 |
| bp-ng45 | 1001 | -13.26 | -7.92 | -8466.77 |
| bp-ng45 | 1002 | -40.18 | -7.89 | -11449.92 |
| bp-ng45 | 1003 | -4.59 | -7.88 | -7530.42 |
| ariane133-ng45 | 1001 | -22.66 | -1.01 | -74.58 |
| ariane133-ng45 | 1002 | -24.34 | -0.55 | -132.46 |
| ariane133-ng45 | 1003 | 77.74 | -0.28 | -1.71 |
