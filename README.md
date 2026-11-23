# 美食高表现视频周报

流程：**Codex直接浏览美食赛道 → Python筛选和比较互动 → Codex看入选原视频 → Python组装Markdown周报**。

目标是找有数据支持、值得借鉴的美食内容；关键词只是发现入口。只有进入样本的数据能被比较，不能把样本前列称为全平台前列。

|阶段|Skill指导Codex|Python脚本|
|---|---|---|
|Discovery|选入口与排序，打开详情，当场记录完整链接和公开字段，每5条保存|导入JSONL，冻结来源与配置|
|Pipeline|查看数量和覆盖缺口|筛视频和相关性、去重、按同平台累计指标生成优先核验清单|
|Verification|重点看候选视频/字幕，判断内容形式及借鉴价值，记录证据|校验核验记录并保留版本|
|Reporting|检查结论和成稿|计算数量、按MD母版01–08栏目生成草稿|

## 使用
Python3.11+；Windows如缺时区数据库安装tzdata。浏览器工具由Codex环境提供。先阅读[采集规则](COLLECTION_STANDARD.md)，再按[数据格式](DATA_FORMAT.md)保存本地记录。
config/weekly.json设置本次出刊编号周期和运行基准；视频发布日期不限，未知日期也不阻塞采集。首次运行可自动冻结基准，复现测试须固定observation_cutoff。

```sh
python run_pipeline.py discovery --run-id 2026-1115-1121-test --input-root /local/records
python run_pipeline.py screen --run-id 2026-1115-1121-test
python run_pipeline.py verify --run-id 2026-1115-1121-test --checks /local/checks.jsonl
python run_pipeline.py report --run-id 2026-1115-1121-test
```

每次只执行用户指定阶段。结果在data/runs/<run-id>/，仅保留完整源记录与筛选理由。Discovery和screen不覆盖；补核验后可重跑verify/report并保留版本。数据只在本地，GitHub维护代码/规则/母版。
周报编号为2026-1115-1121，条目追加-001；视频身份为平台:原ID。滚动时间在正文精确注明。没有跨批次候选池，修改来源/配置需新run。

## 文件
- .agents/skills/food-trend-weekly/SKILL.md：给Codex的执行说明。
- run_pipeline.py：命令入口；workflow.py：四阶段脚本。
- pipeline/browser_records.py：浏览器记录适配；common.py：基础筛选函数；priority.py：互动优先级。
- config/：周期和版本化参数；MD母版：报告栏目来源。
- test_browser_records.py、test_priority.py：离线行为测试。
- verify_reproducibility.py：给定相同浏览器记录和固定配置的两次复现检查。

```sh
python test_browser_records.py
python test_priority.py
python verify_reproducibility.py --input-root /local/records --config /local/fixed_config.json
```

调用示例：“读取本仓库food-trend-weekly Skill，直接找美食高表现候选，先执行Discovery并保存完整详情后停止。” Skill是否自动加载取决于客户端，可直接指定其路径。

现有脚本不自动操作浏览器、不绕过验证、不保证找全爆款。不完整记录补不齐就丢弃；完整性门槛和配额见采集规则，平台可能无法提供必需字段。没有定时任务或默认Google Docs发布。仓库维护遵循AGENTS.md，以新规则替换重复/过时内容；历史从Git追溯。


三个平台均不限发布时间，不设置最近一周、最低24小时或年龄组。报告日期范围仅标识出刊周期；入选是采集时累计表现较高的案例，不代表本周新爆款。
