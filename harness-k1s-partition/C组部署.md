# C 组部署

压缩包 `C-K1S-partition.zip` 从 `AgenticBench/agent/loss_decoder/` 开始，包含 11 个 Agent 文件。使用 C 组独立的官方源码副本、既有数据和镜像配置，在源码根目录解压。选一个全新的运行目录保存本次实验。

```bash
unzip /path/to/C-K1S-partition.zip -d /path/to/C/contest-source
cd /path/to/C/contest-source/AgenticBench
python3 -m contest2 check --baseline loss_decoder --work-root /path/to/C/runs/partition-01
python3 -m contest2 run --baseline loss_decoder --work-root /path/to/C/runs/partition-01
```

路径替换成 C 组实际位置。如原来通过脚本显式传入镜像、源码、矩阵、数据或密钥文件参数，沿用这台机已验证的配置。`check` 检查运行环境，`run` 启动计费实验。主机上已有的其他运行目录和 Agent 模板应指向各自独立的副本。

## 怎么看第一份回执

本次运行目录下的 `participant-agent/loss_decoder/search.jsonl` 按事件记录结果。

- 在 `submitted.partition_forecasts` 看生成时预报的分层变化、物理指标及反证条件。
- 在 `submitted.synthetic_check` 看小图父子梯度的相对差异、方向及一步更新后的边界换层。合成图的输出发生在物理合法化前。`unavailable` 表示缺少运行依赖，`inconclusive` 表示此次测量无结论。
- 在 `evaluated.forecast_check` 看逐算例、逐种子的换层比例和消除整层翻转后的比例，两者都以官方初始分层为参照。WNS、TNS 或分数按实际父候选配对，首次使用官方发布的起点测量时，字段 `parent_source` 会注明。完整有效矩阵才给预测标注 `met` 或 `missed`。例如 `tns majority up` 表示九组中至少五组的 TNS 比配对父版更接近零。
- 从第二份完整回执起，在下一次生成请求查看 `parent_program`、`prior_forecast_checks` 和 `supervisor_review`。开局专家知识只写入首次生成请求。监督器使用本次运行的回执，给出继续或临时换父版的决定。

本地复验入口为 `tests/verify_release.py`，测试脚本和历史回执位于部署包外。回放修改了历史候选的说明以适配新字段，沿用原回执，不能用作新版得分。
