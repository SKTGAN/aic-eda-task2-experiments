# 第 2 轮

实际父候选 `1db68b580dcc9c60efff3352cc8ba2178c6de6f49e52be544319e3b6eb94c72b`。候选 `8e091d7ca30751b53cb84fd649a309db6606e3148515e0f6fe576bc471c2bf11`。范围 distribution snapshot，账本状态 accepted，已取得 3/9 组，完整分 **—**。

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
  "loss": "Negative sampling plus timing-weighted star-edge attraction. Change: retain the maintained random-walk negative-sampling objective, but add a normalized regularizer that raises cosine similarity along"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1003 | 0.00 | -0.64 | -188.35 |
| bp_fe-ng45 | 1002 | 0.00 | -0.73 | -211.75 |
| bp_fe-ng45 | 1001 | -71.49 | -0.99 | -324.35 |
