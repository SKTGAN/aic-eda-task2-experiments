# 给 Claude 的赛题二审计包
本次交付要解决一个问题：旧 Claude Harness 为什么能在一次正式九组训练中生成 34.754996 分的候选，怎样把可复用的专业判断保留下来，并用一次尽可能单纯的改动验证它？请先读 [Claude 任务书](CLAUDE_TASK.md)。请最终交付可运行的修订代码及测试。

| 阅读顺序 | 材料 | 要核对的问题 |
|---|---|---|
| 1 | [队伍的完整思考](brief/USER_INTENT.md) · [用户原图](brief/original-user-notes.png) | 本次优先级、探索与保优、局部实验、自评和并行分别解决什么 |
| 2 | [34.75 版审计](EXPERT_AUDIT.md) · [第 2 轮](runs/15332-claude-original-34/round-02/) · [第 4 轮](runs/15332-claude-original-34/round-04/) | 确认实际父版、改了哪个函数，以及收益来自哪些种子 |
| 3 | [六台机器和各运行](MACHINES.md) · [逐轮表](data/rounds.csv) · [逐组表](data/cells.csv) · [昨天时间窗口](data/nov18-timeline.csv) | 比较不同 Harness 的搜索决策、重复结果、异常和回退 |
| 4 | [可编辑的旧版 Harness](edit-this/AgenticBench/agent/loss_decoder/) · [官方开发说明](rules/official-README.md) · [专家知识说明](rules/offline-expert-policy.pdf) | 以原版 Harness 为开发基础，从官方初始算法执行；先做知识修订 |
| 5 | [证据说明与缺口](EVIDENCE.md) · [开始前核对列](data/run-index.json) | 分清模型真实输入、候选作者公开写下的假设，以及审计者的归因 |

各运行的 `round-NN/generation.json` 保存该轮关联到的请求、回复、复核以及提交理由，`candidate.py` 为实际候选，`receipt.json` 保存账本状态、物理回执和已记录的逐组反馈。没有正文的轮次会明确保留空白。完整的运行级事件顺序在 `events.jsonl` 中。打开候选版本之前，请先看实际父 ID，前一轮未必是父版。

本包含队伍算法、生成记录和只读评分证据，供此次 Claude 审计使用。正式 Agent 只需其选定的开发目录和规则允许的文件。
