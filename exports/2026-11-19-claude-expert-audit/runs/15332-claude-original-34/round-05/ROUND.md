# 第 5 轮

实际父候选 `6a8e3ef053a9119bf4daadc0d3bf7f8b8b804d7f0d1e499986ab2f30f4f09edd`。候选 `bd957b3c95d402b1aff7b856d29978a1006355a27d455cc756788d1936957c44`。范围 official-runner，账本状态 succeeded，已取得 9/9 组，完整分 **25.12**。

## 模型当时可见的信息

没有收录可直接关联本轮提交的模型请求正文。固定 Harness 模板、上一轮回执和计量可单独核对。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "assignment_unchanged",
  "candidate_id": "6a8e3ef053a9119bf4daadc0d3bf7f8b8b804d7f0d1e499986ab2f30f4f09edd"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Relative to the parent timing-weighted star-edge attraction, this substitutes an area-mobility-weighted edge mean read from the published graph endpoints and node_areas. Small movable standard-cell su"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | 29.23 | -1.01 | -309.93 |
| bp_fe-ng45 | 1002 | 35.77 | -0.73 | -379.44 |
| bp_fe-ng45 | 1003 | 62.61 | -0.57 | -143.19 |
| bp-ng45 | 1001 | -11.16 | -7.86 | -8264.33 |
| bp-ng45 | 1002 | -35.52 | -7.85 | -10959.29 |
| bp-ng45 | 1003 | -1.38 | -7.93 | -7147.70 |
| ariane133-ng45 | 1001 | 57.76 | -0.40 | -18.91 |
| ariane133-ng45 | 1002 | 25.94 | -0.46 | -63.36 |
| ariane133-ng45 | 1003 | 62.82 | -0.46 | -4.43 |
