# 27528-ablation

采集端口 16012，UTC 2026-11-19T04:14:37.767042+00:00。交互按 JSONL 的实际记录顺序保存。缺少正文的模型调用只保存计量或日志中已有的决策。

|轮|完整分|已有组|应有组|账本状态|请求事件|响应事件|搜索方向|父候选前缀|
|---:|---:|---:|---:|---|---:|---:|---|---|
| 1 | 4.98 | 9 | 9 | succeeded | 2 | 2 | loss_only | 1419acdef8 |
| 2 | -3.61 | 9 | 9 | succeeded | 2 | 2 | repair | 012b248b2d |
| 3 | 12.76 | 9 | 9 | succeeded | 4 | 4 | decoder_only | 012b248b2d |
| 4 | 11.79 | 9 | 9 | succeeded | 2 | 2 | diversify | 1419acdef8 |
| 5 | -6.28 | 9 | 9 | succeeded | 2 | 2 | loss_only | 1419acdef8 |
| 6 | 12.53 | 9 | 9 | succeeded | 2 | 2 | loss_only | 1419acdef8 |
| 7 | -100.00 | 9 | 9 | succeeded | 2 | 2 | diversify | 1419acdef8 |
| 8 | -6.08 | 9 | 9 | succeeded | 2 | 2 | diversify | 1419acdef8 |
| 9 | — | 8 | 9 | accepted | 2 | 2 | loss_only | 1419acdef8 |
