# 赛题二 `loss_decoder` Agent

`AgenticBench/agent/loss_decoder` 是可放入官方任务包的完整 Agent 目录。它读取任务包中官方初始源码，通过受控模型接口生成完整候选，先调用官方静态验证，再等待官方训练矩阵出分，并保存得分最高的有效候选。分数相同且两版都有完整 TNS 指标时，比较平均 TNS 改善率。`search.jsonl` 保存运行中实际产生的评估和父候选关系。

前两次评估都从官方起点出发，分别改变损失函数和解码器。可以在 Agent 目录用 `opening.txt` 指定 `decoder_only` 为第一条路线。提示要求模型依据官方接口说明核实原算法，并说明预期效果和可否证的结果。

后续比较候选和实际父版本的同种子成绩。若多数种子改善、少数种子严重退步，Agent 优先安排一次定向修补。若多数种子退步，Agent 换机制，并在现有候选均未超过起点时回到官方起始程序。明确的候选接口错误帮助选择需要修的组件，资源故障用作环境诊断。搜索理由随提交记录保存。最终选优依据是官方训练矩阵总分，最优程序每次刷新时立即落盘。

每轮反馈带有候选与实际父版本的逐组对照。官方初始程序对应的对照取自任务包发布的训练测量。最大单组退步同时显示封底前 WNS 和 TNS 的分数贡献。失败按可核实的阶段、原因和日志摘要呈现，明确的资源环境错误和候选接口错误附类型。模型还会收到一条来自同次运行的相关旧实验，优先匹配失败阶段或算例与种子。 [EDA-Debugger](https://www.isqed.org/English/Proceedings/pdf/2A-1-008.pdf) · [AlphaEvolve](https://arxiv.org/abs/2506.13131)

`prompt.md` 末尾声明了 154 个计数单位的离线专家知识，只随独立运行的第一次模型请求发送。内容概括了二维时序线索、三维合法化、层归属、跨种子对照以及组合改动的验证。正式后续提示使用官方任务材料和该次运行自身的评估反馈。

搜索策略参考 AlphaEvolve 保留已评估候选和探索不同父程序的思路。TP-GNN 原论文区分了学习节点表示和聚类分层两步，DREAMPlace 4.0 与 Open3DBench 帮助理解时序指标与物理合法化之间的关系。本 Agent 未复用论文实现。 [AlphaEvolve](https://arxiv.org/abs/2506.13131) · [TP-GNN](https://gtcad.gatech.edu/www/papers/DAC20_TP-GNN.pdf) · [DREAMPlace 4.0](https://guozz.cn/publication/tddp-tcad-23/tddp-tcad-23.pdf) · [Open3DBench](https://arxiv.org/abs/2503.12946)

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
