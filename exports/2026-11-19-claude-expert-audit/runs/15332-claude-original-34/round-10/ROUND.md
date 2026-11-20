# 第 10 轮

实际父候选 `6a8e3ef053a9119bf4daadc0d3bf7f8b8b804d7f0d1e499986ab2f30f4f09edd`。候选 `44734b41501fe91605a5feb2ef63f765aab2cd81c9a16c1edaac96553bd9f632`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **10.55**。

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
  "decoder": "Relative to the parent custom area-balanced two-means decoder, replace the distance-margin ranking by a seeded area-weighted variance-axis projection refined with an iterative Fisher between-group dir"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 55.81 | -0.63 | -195.65 |
| bp_fe-ng45 | 1002 | 42.05 | -0.77 | -283.38 |
| bp_fe-ng45 | 1003 | 56.11 | -0.61 | -198.90 |
| bp-ng45 | 1001 | -19.48 | -7.90 | -9164.73 |
| bp-ng45 | 1002 | -49.25 | -7.83 | -12485.54 |
| bp-ng45 | 1003 | -7.68 | -8.30 | -7653.64 |
| ariane133-ng45 | 1001 | 35.22 | -0.53 | -39.49 |
| ariane133-ng45 | 1002 | 82.21 | -0.20 | -4.64 |
| ariane133-ng45 | 1003 | -100.00 | -0.88 | -1269.63 |
