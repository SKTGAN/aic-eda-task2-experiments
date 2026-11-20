# 第 9 轮

实际父候选 `6a8e3ef053a9119bf4daadc0d3bf7f8b8b804d7f0d1e499986ab2f30f4f09edd`。候选 `eb8d17076588920895968ad74ae866ab95b2e2fae3edd3243320fd1bbd67f9c6`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **28.41**。

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
  "loss": "Relative to the parent timing-weighted star-edge attraction, add a per-net importance factor read from the published net_weights and graph_net_ids. The star-edge term remains a normalized weighted mea"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 51.62 | -0.64 | -240.32 |
| bp_fe-ng45 | 1002 | 35.77 | -0.73 | -379.44 |
| bp_fe-ng45 | 1003 | 62.61 | -0.57 | -143.19 |
| bp-ng45 | 1001 | -27.11 | -7.85 | -10030.15 |
| bp-ng45 | 1002 | -35.52 | -7.85 | -10959.29 |
| bp-ng45 | 1003 | 3.52 | -7.89 | -6628.03 |
| ariane133-ng45 | 1001 | 18.33 | -0.65 | -51.80 |
| ariane133-ng45 | 1002 | 87.54 | -0.11 | -6.12 |
| ariane133-ng45 | 1003 | 58.94 | -0.45 | -11.37 |
