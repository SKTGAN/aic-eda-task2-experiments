# 第 4 轮

实际父候选 `9fae09f57b95c03259e71450d86f242bd4ff63ba9646d529d0a519e7d1c478c9`。候选 `6a8e3ef053a9119bf4daadc0d3bf7f8b8b804d7f0d1e499986ab2f30f4f09edd`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **34.75**。

## 模型当时可见的信息

没有收录可直接关联本轮提交的模型请求正文。固定 Harness 模板、上一轮回执和计量可单独核对。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "explore_from_incumbent",
  "candidate_id": "9fae09f57b95c03259e71450d86f242bd4ff63ba9646d529d0a519e7d1c478c9"
}
```

候选或日志中的公开设计说明：

```json
{
  "decoder": "Relative to the parent, keep the timing-weighted star-edge loss unchanged and replace the frozen two-means helper with a custom seeded area-balanced two-means decoder. Initial centers are an embedding"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 55.81 | -0.63 | -195.65 |
| bp_fe-ng45 | 1002 | 54.06 | -0.66 | -199.47 |
| bp_fe-ng45 | 1003 | 56.09 | -0.60 | -204.56 |
| bp-ng45 | 1001 | -15.37 | -7.83 | -8746.73 |
| bp-ng45 | 1002 | -49.25 | -7.83 | -12485.54 |
| bp-ng45 | 1003 | -1.38 | -7.93 | -7147.70 |
| ariane133-ng45 | 1001 | 82.97 | -0.22 | -0.94 |
| ariane133-ng45 | 1002 | 72.42 | -0.25 | -13.96 |
| ariane133-ng45 | 1003 | 57.44 | -0.45 | -13.74 |
