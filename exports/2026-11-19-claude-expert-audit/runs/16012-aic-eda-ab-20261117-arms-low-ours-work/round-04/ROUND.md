# 第 4 轮

实际父候选 `2f5e1997129df8af708f6db7a3df3d1b60c043cae483118bff18deee84bd6bbe`。候选 `c70ae3e4f0382868c7e0486a39992aee5be8ab796c42617c58df9df367284a9c`。范围 official-runner，账本状态 failed，已取得 9/9 组，完整分 **—**。

## 模型当时可见的信息

没有收录可直接关联本轮提交的模型请求正文。固定 Harness 模板、上一轮回执和计量可单独核对。

[按次完整请求、可见回复、拒绝记录与提交决定](generation.json) · [所在运行完整事件流](../events.jsonl)

## 可核实的理由

提交时保存的决定：

```json
{
  "reason": "runtime_environment_failure",
  "candidate_id": "6bc564c56f0461cbe67dc5f077f5ec9a9111e9e903131a19fbd2b4b77f9868a4"
}
```

候选或日志中的公开设计说明：

```json
{
  "loss": "Diversify vs parent: retain the maintained random-walk contrastive term (positives attracted, sampled negatives pushed apart) and add one timing- weighted star-edge cohesion term over the supplied ``g"
}
```

[实际候选代码](candidate.py) · [账本、逐组物理结果和已记录反馈](receipt.json)

| 算例 | 种子 | 分项分 | WNS(ns) | TNS(ns) |
|---|---:|---:|---:|---:|
| bp_fe-ng45 | 1001 | — | — | — |
| bp_fe-ng45 | 1002 | — | — | — |
| bp_fe-ng45 | 1003 | — | — | — |
| bp-ng45 | 1001 | — | — | — |
| bp-ng45 | 1002 | — | — | — |
| bp-ng45 | 1003 | — | — | — |
| ariane133-ng45 | 1001 | — | — | — |
| ariane133-ng45 | 1002 | — | — | — |
| ariane133-ng45 | 1003 | — | — | — |
