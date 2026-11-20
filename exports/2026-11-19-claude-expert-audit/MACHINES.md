# 机器与成绩索引

机器端口用于关联保留盘。原 15332 的目录从 13624 读取，10820 从 15416 读取，27528 从 16012 读取。训练时硬件和采集时硬件可能不同。

|运行|采集端口|有完整分的轮数 / 提交|训练或诊断最高|公开验证|已记录请求 / 响应事件|
|---|---:|---:|---:|---:|---:|
| [15332-claude-v3](runs/15332-claude-v3/README.md) | 13624 | 10 / 10 | 29.67 | — | 24 / 24 |
| [15332-claude-original-34](runs/15332-claude-original-34/README.md) | 13624 | 10 / 10 | 34.75 | -4.35 | 0 / 0 |
| [10820-branching](runs/10820-branching/README.md) | 15416 | 10 / 10 | 27.50 | -19.11 | 15 / 15 |
| [10820-evidence](runs/10820-evidence/README.md) | 15416 | 4 / 4 | 26.49 | — | 11 / 11 |
| [16012-aic-eda-ab-20261117-arms-contract-ours-work](runs/16012-aic-eda-ab-20261117-arms-contract-ours-work/README.md) | 16012 | 0 / 0 | — | — | 0 / 0 |
| [16012-aic-eda-ab-20261117-arms-contract-claude-work](runs/16012-aic-eda-ab-20261117-arms-contract-claude-work/README.md) | 16012 | 0 / 0 | — | — | 0 / 0 |
| [16012-aic-eda-ab-20261117-arms-ours-work](runs/16012-aic-eda-ab-20261117-arms-ours-work/README.md) | 16012 | 0 / 0 | — | — | 0 / 0 |
| [16012-aic-eda-ab-20261117-arms-claude-work](runs/16012-aic-eda-ab-20261117-arms-claude-work/README.md) | 16012 | 0 / 0 | — | — | 0 / 0 |
| [16012-aic-eda-ab-20261117-arms-low-ours-work](runs/16012-aic-eda-ab-20261117-arms-low-ours-work/README.md) | 16012 | 0 / 5 | — | — | 0 / 0 |
| [16012-aic-eda-ab-20261117-arms-low-claude-work](runs/16012-aic-eda-ab-20261117-arms-low-claude-work/README.md) | 16012 | 0 / 1 | — | — | 0 / 0 |
| [27528-previous](runs/27528-previous/README.md) | 16012 | 4 / 5 | 18.22 | — | 14 / 14 |
| [27528-ablation](runs/27528-ablation/README.md) | 16012 | 8 / 9 | 12.76 | — | 20 / 20 |
| [27528-claude-formal-2r](runs/27528-claude-formal-2r/README.md) | 16012 | 2 / 2 | 1.79 | -16.56 | 5 / 5 |
| [27528-claude-diagnostic](runs/27528-claude-diagnostic/README.md) | 16012 | 3 / 3 | 30.98 | — | 6 / 6 |
| [22120-independent](runs/22120-independent/README.md) | 22120 | 10 / 10 | 32.68 | — | 23 / 23 |
| [22120-empty-prep](runs/22120-empty-prep/README.md) | 22120 | 0 / 0 | — | — | 0 / 0 |
| [22120-distribution-staged-snapshot](runs/22120-distribution-staged-snapshot/README.md) | 22120 | 1 / 2 | 0.85 | — | 0 / 0 |
| [26016-two-round](runs/26016-two-round/README.md) | 26016 | 1 / 1 | 17.60 | — | 6 / 5 |
| [30924-rolling-initial](runs/30924-rolling-initial/README.md) | 30924 | 0 / 10 | — | — | 18 / 18 |
| [30924-rolling-v2](runs/30924-rolling-v2/README.md) | 30924 | 3 / 5 | 23.42 | — | 14 / 14 |
