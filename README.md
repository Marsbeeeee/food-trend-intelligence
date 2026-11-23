# 美食高表现视频周报

流程：浏览器采集 → Python整理和筛选 → 查看器复查 → Markdown周报 → 可选Word/PDF。

三个平台的视频发布时间均不限。报告周期只标识出刊编号，归档日期按data/YYYY/MMDD保存，实际采集时间另记。累计互动不是增长，样本前列不是全平台热榜。

## 开始使用

使用Python3.11+，在仓库根目录运行：

```sh
python -m pip install -e .
python run.py --help
python run.py test
```

所有阶段由run.py进入，一次只执行用户指定的阶段：

```sh
python run.py collect init --date 2026-12-05
python run.py collect status --date 2026-12-05 --show-ids
python run.py discovery --run-id 2026-1205-screen --input-root data/2026/1205
python run.py screen --run-id 2026-1205-screen
```

collect管理本地记录和进度，不会自行浏览；discovery导入已有文件，不会重新采集。复查时用浏览器打开[viewer/index.html](viewer/index.html)，选择本地候选JSONL。

只有复查标记时生成明确标记的review-report草稿；有完整内容证据时走verify/report。母版保留01–06，第05节完整明细固定为表格。Word导出安装`python -m pip install -e ".[export]"`；自动PDF另需LibreOffice，也可在Word中另存PDF。全部命令与输出见[使用说明](docs/usage.md)。

## 目录与说明

| 位置 | 用途 |
| --- | --- |
| .agents/skills/food-trend-weekly/ | Codex执行指引，协调现有程序 |
| config/ | collection.json采集与完整性；screening.json筛选；report.json报告设置 |
| templates/weekly_report.md | Markdown母版 |
| pipeline/ | 采集管理、标准化、筛选、核验、报告和导出程序 |
| tests/ | 离线测试与重复运行检查 |
| docs/ | [流程职责](docs/workflow.md)、[使用说明](docs/usage.md)、[数据格式](docs/data_format.md)、[采集规则](docs/collection.md) |
| data/ | 本地日期归档、复查、成稿和运行记录；整个目录被Git忽略 |
| viewer/ | 原有可复用查看器，目录保持原样 |

平台页面操作分别见[抖音](docs/collection/douyin.md)、[小红书](docs/collection/xiaohongshu.md)、[B站](docs/collection/bilibili.md)。参数、字段与规则以对应文件为唯一来源，不在Skill里重复定义。

## 数据与仓库维护

GitHub只同步程序、配置、母版、说明与测试。data整个目录不再跟踪；本地文件不会因忽略规则被清理，历史Git记录不重写。Cookie、登录令牌、浏览器会话、运行缓存也不提交。

拉取仓库后需要自己的本地数据；测试使用合成记录，不要求附带真实样本。旧run保持冻结，不因目录调整重写manifest或重新计算已归档结果。维护遵循[AGENTS.md](AGENTS.md)。

调用示例：“使用本仓库food-trend-weekly，归档日期2026-12-05，每平台60条，完成采集后停止；数据只保存本地。” Skill是否自动加载由客户端决定，也可直接指定其路径。
