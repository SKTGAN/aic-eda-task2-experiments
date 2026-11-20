# 第四台 RTX 3090 的 Harness 评估

Claude 两段补丁是起点，保留多组收益父版本、单组收益与翻层分类、具体失败反馈、有限重试。第四版把同机起点记录区分为实测与混合估计；同一层分配的重复回执只要时序冲突，就剔除该组的推算起点。最终选优仍按官方完整矩阵分。模型首次收到简短专家知识，未预置任何旧候选。

`next-harness/AgenticBench/agent/loss_decoder/` 是可部署的 Agent。`development/diagnose_harness.py` 是独立小测入口，固定种子 1002，同时覆盖三个训练算例，单任务 9 GiB。它只产生带 `formal: false` 的开发回执。正式评估每个任务需 24 GiB，加宿主余量共需至少 28 GiB 可用内存；正式任务包没有改动。

本地回放：`python -B -m unittest discover -s tests -v`。

2026-11-18 扩容后，服务器有 47 GiB 内存，启动时可用 45 GiB。实跑使用官方 `contest2 run --baseline loss_decoder` 入口，按 3 个算例和 3 个种子评估，每次执行一个物理任务。官方镜像的 CUDA 自检与模型鉴权均已通过。

本轮进程由 `aic-eda-fourth-live.service` 管理，工作目录为 `/root/aic-eda-fourth/arm/run-01`，日志为 `/root/aic-eda-fourth/arm/live.log`。启动前有一次模型连通性检查失败，记录保留在同级的 `work` 目录，当时模型调用和评估均为零。
