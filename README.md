# Food Trend Intelligence

**海外“硬汉做面包”对标账号与视频情报工作流**

在 **Instagram、TikTok、YouTube** 发现硬汉形象或人设、同时持续制作面包的账号。先汇总候选，再由人工挑选几个值得研究的账号，最后比较其日常与高流量视频的内容差异。

不设粉丝、播放量门槛；已有粉丝积累但近期播放低的账号也可以保留。粉丝和流量是观察信息，不自动证明人设或面包内容受欢迎。

## 当前流程

| 阶段 | 做什么 | 输出 |
| --- | --- | --- |
| 发现账号 | 平台搜索、搜索引擎和创作者公开互链，核实主页、人设与面包内容 | 候选账号清单 |
| 人工选择 | 综合匹配度、内容特点与历史积累，标为入选、候补、淘汰或待确认 | 选择及理由 |
| 采视频 | 仅针对入选账号，采连续日常样本，另补历史高表现作品 | 视频及互动快照 |
| 内容对照 | 观看原视频或读取可靠字幕，逐条记录面包、人设、开头和拍摄表达 | 明细表及待编辑的观察草稿 |

**默认只执行账号发现阶段，交付候选清单后停止，不自行挑定账号并批量分析视频。** 用户要求后续阶段时再执行。

搜索顺序为 Instagram → TikTok → YouTube，YouTube 优先 Shorts。多个平台的同一人物合并人物 ID，但每个平台仍保留独立账号记录；合并必须有互链或其他身份依据。相似用户名不能单独证明同一人。

## 快速开始

需要 Python 3.11+。在仓库根目录运行：

```sh
python -m pip install -e .
python run.py --help
python run.py test
python run.py accounts init --date 2026-11-24
```

初始化只创建本地文件和配置快照，**不会打开平台或自动搜索**。浏览器或联网搜索负责发现账号，脚本负责校验、去重、统计和生成报告。

向 Codex 下达任务示例：

> 在 Instagram、TikTok、YouTube 搜索“硬汉形象＋持续做面包”的对标账号。不设流量门槛，核实主页并汇总候选；同一人物跨平台记录关联依据。归档日期为 2026-11-24，生成候选清单后停止，先不采视频。

按 [字段说明](docs/data_format.md) 将观察写入初始化生成的 accounts.jsonl。每行一个 JSON 对象。再运行：

```sh
python run.py accounts validate --folder data/2026/1124/benchmarks
python run.py accounts report --folder data/2026/1124/benchmarks --output data/runs/2026-1124-accounts-01
```

选择账号后，记录 reviews.jsonl；后续视频进入 videos.jsonl：

```sh
python run.py videos validate --folder data/2026/1124/benchmarks
python run.py videos compare --folder data/2026/1124/benchmarks --output data/runs/2026-1124-compare-01
```

输出目录必须是新目录，报告保留输入快照和 SHA-256 清单，不覆盖旧版。没有内容证据的字段显示“待补”，不根据标题自动推断视频内容。生成的是供编辑复查的对照草稿，不自动写营销方案或因果结论。

## 配置与文件

| 位置 | 用途 |
| --- | --- |
| [config/collection.json](config/collection.json) | 三平台、搜索方向、不设流量门槛、账号阶段停止点 |
| [config/screening.json](config/screening.json) | 人工选人、视频比较口径 |
| [config/report.json](config/report.json) | 两阶段报告母版 |
| [pipeline/benchmarks.py](pipeline/benchmarks.py) | 当前账号与视频处理 |
| [templates/account_report.md](templates/account_report.md) | 候选账号清单 |
| [templates/account_comparison.md](templates/account_comparison.md) | 普通／高流量内容对照 |
| [viewer/](viewer/) | 旧视频候选的本地查看器；不兼容新账号 JSONL |
| data/YYYY/MMDD/benchmarks/ | 原始观察、选择与配置快照 |
| data/runs/ | 独立报告版本及冻结输入 |

所有原始观察、选择、成稿和运行输出仍放在 data/，Git 忽略。Cookie、API Key 和会话不能提交。

## 比较与交付

不跨平台混算播放，不把 Shorts 和长视频混算。基线来自明确标记的连续日常样本，使用播放中位数；至少 10 条有可比较播放数的样本才计算倍数。这个数量只约束统计基线，不是账号入选门槛。近期开新视频、置顶、商业合作等情况写入采样理由，历史爆款不混入日常基线。普通／高表现分组由人工给出理由，程序不自动认证爆款。

已有数据不可改写或清空；旧的国内三平台工作流已从 run.py 退出。config/legacy/ 与既有 pipeline 模块仅用于历史回归测试和记录解释，不是当前采集规则；旧模板 [weekly_report.md](templates/weekly_report.md) 保留供历史稿使用。

可继续用 export 将完成的 Markdown 转 Word；PDF 仍需要 LibreOffice，导出后需检查实际渲染。本次变更没有生成 Word/PDF。

更多说明：[操作命令](docs/usage.md) · [采集规则](docs/collection.md) · [字段](docs/data_format.md) · [职责](docs/workflow.md) · [维护约定](AGENTS.md)。

