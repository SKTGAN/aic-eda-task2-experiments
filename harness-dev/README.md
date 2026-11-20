# 赛题二 `loss_decoder` Agent

这是供下一次独立运行使用的开发版。

`AgenticBench/agent/loss_decoder` 是可放入官方任务包的完整 Agent 目录。它读取任务包中官方初始源码，通过受控模型接口生成完整候选，先调用官方静态验证，再等待官方训练矩阵出分，并保存得分最高的有效候选。分数相同且两版都有完整 TNS 指标时，比较平均 TNS 改善率。`search.jsonl` 保存运行中实际产生的评估和父候选关系。

前两次评估都从官方起点出发，分别改变损失函数和解码器。如果已有候选都未超过官方发布的初始分，在偶数次评估后回到官方起点试新机制。后续也可改进现有候选。每过两次未刷新最优记录的评估，优先尝试在当前最弱算例上表现更好的备选候选。若没有这样的候选，就按整矩阵总分选择备选，或回到原始起点继续探索。

独立运行可在 Agent 目录的 `opening.txt` 写入 `decoder_only`，调换前两轮的顺序。两台机器可由此并行验证两个方向。每次官方完整矩阵刷新最优候选时，Agent 会更新运行目录中的 `program.py`，供查看当时已验证的最佳程序。

模型收到各算例的均分、最差种子，以及每组的 WNS、TNS、切割网数和时序加权切割量。同算例同种子的变化量优先与实际父候选比较，反馈会注明比较对象是当次评估回执还是任务包发布的初始测量。初始测量只从官方表读取本次训练组，供搜索对照。反馈保留原始分、封底后的计分和可用的原生错误摘要。缺失的测量值会保持缺失。最终按当次官方训练矩阵总分选优。

每轮请求附带同一次运行的实验记录，包括实际父候选、改动位置、模型提出的假设、各算例均分和同父候选比较的种子胜平负。最初两轮以官方初始程序为父候选。实验记录里的胜平负需要候选和父版本都有对应的官方种子成绩。改动记录保存在官方运行工作区，断点续跑时随官方评估记录恢复。只有注释或文档字符串变化的候选会被识别为重复。

`prompt.md` 末尾声明了 154 个计数单位的离线专家知识，只随独立运行的第一次模型请求发送。内容概括了二维时序线索与三维合法化、层归属、跨种子比较和组合改动验证。正式后续提示使用官方任务材料和该次运行自身的评估反馈。

搜索使用 AlphaEvolve 的候选保留思路，以及 GEPA 和 Self-Debugging 中利用评估过程与执行错误做归因的思路。实验历史随下一次候选生成请求发送。 [AlphaEvolve](https://arxiv.org/abs/2506.13131) · [GEPA](https://arxiv.org/html/2507.19457v2#S3) · [Teaching Large Language Models to Self-Debug](https://arxiv.org/abs/2304.05128)

TP-GNN 区分了学习节点表示和聚类分层两步。DREAMPlace 4.0 与 Open3DBench 提供了时序指标与物理合法化的背景。 [TP-GNN](https://gtcad.gatech.edu/www/papers/DAC20_TP-GNN.pdf) · [DREAMPlace 4.0](https://guozz.cn/publication/tddp-tcad-23/tddp-tcad-23.pdf) · [Open3DBench](https://arxiv.org/abs/2503.12946)

在一份独立的官方任务包源码副本中替换 `AgenticBench/agent/loss_decoder`，然后从副本的 `AgenticBench` 目录运行：

```bash
python3 -B -m contest2 check --baseline loss_decoder
python3 -B -m contest2 run --baseline loss_decoder \
  --api-key-file /absolute/private/path/deepseek.key
```

`--api-key-file` 由官方外层进程读取。把 DeepSeek API key 保存在源码、数据和评估工作目录之外，权限设为 `0600`。官方入口也支持交互输入或 `DEEPSEEK_API_KEY` 环境变量。Agent 通过 `context.model.responses_create` 使用官方指定的 `deepseek-flash`，外层负责跟踪实际模型费用和候选评估次数。这个 Agent 不依赖主机上的 Codex CLI。

在云服务器上，用解压任务包的 Linux 账号启动评估并为该运行进程配置 Docker 访问权限。官方容器继承评估进程的 UID，任务包中权限为 `0600` 的文件由解压账号读取。

`check` 用于核对任务包和 CUDA。`run` 真实调用模型并向官方评估器提交候选。正式运行前先使用独立工作目录，确保从干净的官方起点开始。继续同一次运行时复用该目录，Agent 会读取既有评估记录并等待仍在进行的评估。

正式运行返回候选 ID 后，可在同一运行配置下执行公开验证：

```bash
python3 -B -m contest2 validate --baseline loss_decoder \
  --candidate-id <返回的候选ID> --retain-physical-files
```

官方 `validate` 会冻结候选与 Agent。该目录里的 `program.py` 是官方初始程序。正式运行写出的最终 `program.py` 和评估日志在服务器对应的 `contest-work/task2/loss_decoder` 运行目录中。
