# Food Trend Intelligence

**美食视频选例与周报工作流**

从抖音、小红书和 B 站发现高表现美食视频，保留来源与互动快照，通过固定脚本整理候选，再经人工复查生成可追溯的周报。

项目采用 **Codex Skill 协调流程 + Python 脚本处理数据 + 本地查看器复查** 的方式，支持分阶段执行和按日期续采。周报以 Markdown 为主，可导出 Word；PDF 转换需另有可用的转换环境。

> 原数据、复查记录和成稿全部保存在本地 `data/`，整个目录被 Git 忽略。GitHub 只同步程序、配置、母版、说明和测试。

## 导航

- [工作流程](#工作流程)
- [职责分工](#职责分工)
- [快速开始](#快速开始)
- [配置与采集口径](#配置与采集口径)
- [数据与输出](#数据与输出)
- [周报与交付](#周报与交付)
- [项目目录](#项目目录)
- [检查与维护](#检查与维护)

## 工作流程

```text
关键词搜索与采集
       ↓
检查原数据 → 标准化、去重与筛选
       ↓
查看器复查 → 保留、淘汰、待确认及备注
       ↓
按母版生成 Markdown 周报
       ↓
审核后交付，可选导出 Word / PDF
```

| 阶段 | 做什么 | 得到什么 |
| --- | --- | --- |
| 采集 | Codex 操作已登录的平台页面，读取视频信息与互动数据；脚本校验、去重并记录进度 | 三个平台分别保存的原始 JSONL |
| 整理与筛选 | 导入并冻结输入，统一字段，判断美食相关性，同平台比较多项互动表现 | 优先清单、候补清单、待确认项及筛选说明 |
| 人工复查 | 打开候选，访问原视频，标记去留并按需写备注 | 独立的复查 JSON |
| 周报 | 结合复查记录与编辑观察组装报告；有完整内容证据时进入核验流程 | Markdown 报告及可追溯的报告输入、校验记录 |
| 导出 | 转为适合分享的格式，检查分页与链接 | Word；转换环境可用时生成 PDF |

各阶段独立执行，完成指定阶段后停止。当前没有自动定时采集，也不会仅运行一个命令就自动登录、看完视频并完成整份周报。

## 职责分工

| 执行方 | 负责的事 | 对应位置 |
| --- | --- | --- |
| Codex Skill | 读取规则、选择本次阶段、协调浏览器操作、处理登录与异常、检查输出 | [food-trend-weekly](.agents/skills/food-trend-weekly/SKILL.md) |
| Python 脚本 | 管理进度，校验字段、标准化、去重、筛选、计数、生成文件和导出 | [pipeline/](pipeline/)；统一入口 `run.py` |
| 人工复查 | 判断内容是否值得借鉴，确认原视频与内容证据，审核报告结论 | [viewer/](viewer/) 与本地复查记录 |

筛选规则由配置和代码执行，Skill 调用现有程序，不在每次运行时另写算法。详细职责见[流程说明](docs/workflow.md)。

## 快速开始

### 1. 准备环境

需要 **Python 3.11 或以上版本**。下载或克隆仓库后，在仓库根目录运行；建议使用虚拟环境：

```sh
python -m pip install -e .
python run.py --help
python run.py test
```

新下载的仓库不附带真实视频数据。离线测试使用合成记录，不要求先登录平台或准备 `data/`。

### 2. 采集新数据

可以向 Codex 指定阶段与归档日期，例如：

> 使用本仓库的 food-trend-weekly，归档日期为 2026-12-05，按当前配置采集三个平台，每平台目标 60 条。完成采集和完整性检查后停止，数据只保存本地。

执行指引位于[仓库 Skill](.agents/skills/food-trend-weekly/SKILL.md)，也可直接把该路径交给 Codex。实际采集需要可用的浏览器工具与平台登录会话，遇到扫码或访问限制时由用户完成相应操作。

脚本侧用以下命令初始化和查看进度：

```sh
python run.py collect init --date 2026-12-05
python run.py collect status --date 2026-12-05 --show-ids
python run.py collect audit --date 2026-12-05
```

**这些命令只管理文件、进度与校验，不会自行打开网页或采集视频。** 浏览器采集、批量写入和失败记账见[采集与续采说明](docs/collection.md)。

### 3. 整理已有原数据

已有三份完整原始 JSONL 时，先导入，再筛选：

```sh
python run.py discovery --run-id 2026-1205-screen --input-root data/2026/1205
python run.py screen --run-id 2026-1205-screen
```

这里的 `discovery` 表示检查并冻结已有文件，不会重新采集。结果保存在 `data/runs/2026-1205-screen/`。

先阅读 `screen_summary.md`，再用浏览器打开本地 [viewer/index.html](viewer/index.html)，载入 `priority_queue.jsonl` 复查。离开查看器前导出复查记录；复查 JSON 与候选 JSONL 需配套保留。

### 4. 生成报告

| 当前材料 | 使用方式 |
| --- | --- |
| 有候选、查看器复查记录和编辑观察 | `review-report` 生成明确标记的复查后草稿 |
| 已补齐原视频内容证据与 `checks.jsonl` | `verify` 校验证据，再由 `report` 生成核验流程下的报告 |
| 已有审核后的 Markdown | `export` 导出 Word；PDF 需可用的转换环境 |

标记“保留”表示选例决定，不自动代表已经完成视频形式核验。完整命令集中在[使用说明](docs/usage.md)，各命令也支持 `--help`。

## 配置与采集口径

| 配置 | 管什么 |
| --- | --- |
| [collection.json](config/collection.json) | 平台、关键词、采集数量、批次大小、尝试上限与必需字段 |
| [screening.json](config/screening.json) | 同平台比较指标、候选上限与作者数量限制 |
| [report.json](config/report.json) | 报告周期、运行基准、母版与策略引用 |

当前默认关键词为 **美食、烘焙、美食制作**，每平台目标 **60 条完整记录**。筛选阶段每平台最多 **12 条优先候选**，实际数量由数据决定。执行参数以配置为准，比较方法见[筛选规则](docs/usage.md#当前选例规则)。

三个平台均不限制视频发布时间。互动数据是采集当时看到的累计数值，保留约数和下限标记；缺失必需字段不能补零或编造。

**周报按期整理高表现案例，不等于只收录本周发布的视频。** 样本内排名不等于全平台热榜，单次互动快照不能说明增长速度。选题与视频形式的结论仍需要内容证据支持。

平台操作：[抖音](docs/collection/douyin.md) · [小红书](docs/collection/xiaohongshu.md) · [B 站](docs/collection/bilibili.md)。

## 数据与输出

```text
data/                                  # 全部仅留本地，不提交 Git
├── 2026/
│   └── 1205/                           # 归档日期 YYYY/MMDD
│       ├── douyin_original.jsonl
│       ├── xiaohongshu_original.jsonl
│       └── bilibili_original.jsonl
├── collection_state/                   # 按日期记录采集进度与尝试
└── runs/
    └── 2026-1205-screen/               # 本次处理批次的冻结输入与输出
        ├── screen_summary.md
        ├── priority_queue.jsonl
        ├── reserve_candidates.jsonl
        ├── needs_review.jsonl
        └── …
```

需要归档时，将筛选结果、复查文件、成稿和导出文件放入对应的 `data/YYYY/MMDD/`。例如实际有 36 条候选时使用 `priority_36.jsonl`、`priority_36_repo.md`；名称中的数量按真实结果填写。具体字段与身份规则见[数据格式](docs/data_format.md)。

| 日期 | 含义 | 示例 |
| --- | --- | --- |
| 归档日期 | 决定数据目录 | `data/2026/1205/` |
| 周报周期 | 决定出刊编号 | `2026-1115-1121` |
| 实际采集时间 | 说明互动快照是什么时候看到的 | 保存在每条数据中 |
| 视频发布时间 | 平台可见的原视频日期，不决定当前采集范围 | 有明确来源才填写 |

整个 `data/` 已取消 Git 跟踪，忽略规则不会清理本地文件。旧数据仍可能存在于历史提交中，本次未重写 Git 历史。

## 周报与交付

母版位于 [templates/weekly_report.md](templates/weekly_report.md)，正文使用六个部分：

| 部分 | 内容 |
| --- | --- |
| 01 | 本期情报摘要 |
| 02 | 本期美食内容选题 |
| 03 | 内容表达与视频形式 |
| 04 | 重点案例观察 |
| 05 | 完整内容明细，以表格呈现 |
| 06 | 信息核验与采集规则 |

Markdown 可以独立生成和保存，不默认发布 Google Docs。给不使用 Markdown 的同事交付时，可导出 Word：

```sh
python -m pip install -e ".[export]"
python run.py export --input data/2026/1122/美食视频周报_2026-1115-1121.md --output-dir data/2026/1122/export-v2 --format docx
```

输入路径是示例，需替换为本地已有报告。自动生成 PDF 需要安装 LibreOffice 并让 `soffice` 可用，此时可改用 `--format both`；否则先导出 Word，再由 Word 另存 PDF。交付前检查中文、分页、表头和链接。目标文件存在时会拒绝覆盖，可换新输出目录保存修订。

## 项目目录

```text
food-trend-intelligence/
├── .agents/skills/food-trend-weekly/    # Codex 执行指引
├── config/                            # 采集、筛选、报告配置
├── templates/                         # Markdown 周报母版
├── pipeline/                          # Python 处理模块
├── viewer/                            # 本地候选复查查看器
├── tests/                             # 离线测试与复现检查
├── docs/                              # 流程、命令、字段和平台操作
├── data/                              # 本地数据与成稿，Git 忽略
├── run.py                             # 统一命令入口
├── pyproject.toml                     # Python 环境与可选依赖
├── AGENTS.md                          # 仓库维护约定
└── README.md
```

## 检查与维护

```sh
python run.py test
```

离线测试覆盖数值精度、筛选规则、采集管理、报告生成和流程复现，不访问真实平台。固定本地样本的复现检查见[测试命令](docs/usage.md#检查脚本是否正常)；查看器测试按同一文档中的独立命令运行。

已有处理批次的输入、配置与校验记录保持冻结。数据或规则变化时使用新的 `run-id`，不覆盖旧结果。维护按 [AGENTS.md](AGENTS.md) 执行；更新规则时同步替换旧说明，避免保留互相矛盾的版本。

| 要了解的问题 | 阅读位置 |
| --- | --- |
| 每个阶段谁来做、何时停止 | [流程职责](docs/workflow.md) |
| 命令怎么运行、结果怎么看 | [使用说明](docs/usage.md) |
| 字段、视频 ID、链接和数值精度怎么保存 | [数据格式](docs/data_format.md) |
| 采集怎么续跑、补齐和处理失败 | [采集规则](docs/collection.md) |

Cookie、登录令牌、浏览器会话及运行缓存不提交仓库。
