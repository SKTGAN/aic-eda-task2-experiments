# 第 3 轮

实际父候选 `9fae09f57b95c03259e71450d86f242bd4ff63ba9646d529d0a519e7d1c478c9`。候选 `6d3bf02a6b2289083dcaaa37bf2846486ee480d0990e54b25dd310f3b0e2a7fa`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **24.87**。

## 模型当时可见的信息

没有收录可直接关联本轮提交的模型请求正文。固定 Harness 模板、上一轮回执和计量可单独核对。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "refine_incumbent",
  "candidate_id": "9fae09f57b95c03259e71450d86f242bd4ff63ba9646d529d0a519e7d1c478c9"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Relative to the parent loss, keep the timing-weighted star-edge attraction sum_e w_e * softplus(-graph_scores_e) but focus each edge by the endpoint timing criticality read from published node_feature"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 25.47 | -0.89 | -417.04 |
| bp_fe-ng45 | 1002 | 51.88 | -0.65 | -228.43 |
| bp_fe-ng45 | 1003 | 54.16 | -0.63 | -212.50 |
| bp-ng45 | 1001 | -13.11 | -7.83 | -8491.91 |
| bp-ng45 | 1002 | -28.66 | -7.83 | -10213.32 |
| bp-ng45 | 1003 | 0.29 | -7.95 | -6954.33 |
| ariane133-ng45 | 1001 | 5.99 | -0.62 | -75.84 |
| ariane133-ng45 | 1002 | 70.58 | -0.32 | -8.01 |
| ariane133-ng45 | 1003 | 57.20 | -0.43 | -15.94 |
