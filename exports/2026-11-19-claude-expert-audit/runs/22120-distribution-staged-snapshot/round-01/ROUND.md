# 第 1 轮

实际父候选 `1db68b580dcc9c60efff3352cc8ba2178c6de6f49e52be544319e3b6eb94c72b`。候选 `ab770d47c90c2ac3fac7286983ae5ba06cf5dc4384854d4d35c2834aca3f2436`。范围 distribution snapshot，账本状态 succeeded，已取得 9/9 组，完整分 **0.85**。

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
  "decoder": "Deterministic area-balanced two-means decoder. Change: replace the seeded reference clustering with a custom bounded loop that initializes centers from weighted-mean extreme embeddings and applies cum"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 52.59 | -0.63 | -231.69 |
| bp_fe-ng45 | 1002 | 49.92 | -0.69 | -232.29 |
| bp_fe-ng45 | 1003 | 55.82 | -0.64 | -188.35 |
| bp-ng45 | 1001 | -20.82 | -8.39 | -9059.34 |
| bp-ng45 | 1002 | -51.95 | -7.83 | -12781.88 |
| bp-ng45 | 1003 | -14.45 | -7.87 | -8622.28 |
| ariane133-ng45 | 1001 | -100.00 | -0.41 | -274.63 |
| ariane133-ng45 | 1002 | -1.51 | -0.51 | -101.00 |
| ariane133-ng45 | 1003 | 38.09 | -0.57 | -29.77 |
