# 美食视频周报：直接浏览＋Python

新采集由Codex直接浏览抖音、小红书、B站，打开候选详情后立即保存。Python只负责固定数据整理、核验记录校验和Markdown组装；不再调用或依赖MediaCrawler。旧适配器仅保留给历史测试。

## 分工
|阶段|Skill指导Codex|Python|
|---|---|---|
|Discovery|选择平台入口，打开详情，记录完整链接和页面证据，每5条落盘|导入记录、冻结来源和配置|
|Pipeline|查看候选与缺口|统一字段、日期过滤、去重、按平台指标挑核验优先项|
|Verification|看原视频/字幕，核对指标和内容，提供表现依据|检查核验记录并保存版本|
|Reporting|检查证据和成稿|读取MD母版01–08标题，组装报告和日期范围编号|

## 输入
Python3.11+，Windows缺少时区数据时安装tzdata。浏览器操作使用当前Codex可用的浏览器工具，需要用户登录时明确提示。
输入根目录按xhs/、dy/、bili/分别保存JSONL；配置platforms可以仅选当前有数据的平台。每行使用以下字段：

```json
{"schema":"browser_video_v1","content_id":"平台原ID字符串","url":"https://完整原视频链接及必要参数","source_url":"https://发现入口","title":"页面标题","author":"作者","content_type":"video","captured_at":"2026-11-22T20:00:00+08:00","published_at":null,"published_at_display":"2天前","metrics":{"likes":123,"favorites":20,"comments":5,"shares":null},"metrics_display":{"likes":"123"},"detail_status":"partial"}
```

示例不是实际证据。published_at仅在首次发布时间确切且有时区时填写，并补published_at_evidence；相对日期、编辑日期保留原文，精确字段null。metrics只允许精确非负整数/null。评论字段是评论总数，不需要保存评论者内容。完整链接可能过期，不保证永久有效；必须同时保存页面证据和读取时间。格式校验不能代替原页真实性核验。

## 分阶段命令
浏览前先配置一次共同的observation_cutoff T；滚动窗口由此计算。当前默认配置日期为空，正式采集前须固定。选择实际采集的平台。数据不上传GitHub。

```sh
python run_pipeline.py discovery --run-id 2026-1115-1121-test --input-root /local/records
python run_pipeline.py screen --run-id 2026-1115-1121-test
python run_pipeline.py verify --run-id 2026-1115-1121-test --checks /local/checks.jsonl
python run_pipeline.py report --run-id 2026-1115-1121-test
```

结果在data/runs/<run-id>/。原始文件和筛选结果不覆盖；核验及报告支持编号版本。report.md为最新草稿，日期编号文件同时生成。原视频身份与报告条目编号独立。当前只在单次run内去重，跨批次候选池尚未实现。

核验checks每行包含record_id、operator、checked_at、evidence_url、author、published_at（确切首次时间）、content_summary、is_video=true、food_relevant=true、intelligence_type=single_video或trend、performance_basis及metric。metric含name/value/captured_at，name支持views/likes/coins/comments/favorites/shares；trend还需至少2个independent_author_keys。原页日期不足以核实时，不提交正式checks，保留pending。

## 文件
- .agents/skills/food-trend-weekly/SKILL.md：浏览操作与阶段规则。
- run_pipeline.py、workflow.py：命令入口和四步处理。
- pipeline/browser_records.py：直接浏览记录适配。
- pipeline/engine.py：复用基础解析函数，旧main仅供历史兼容。
- config/weekly.json、discovery_policy.json：正式周期与规则；fixture.json为旧数据测试。
- 视频热点情报周报_母版.md：报告栏目。
- verify_reproducibility.py：旧107条兼容回归；test_browser_records.py：直接浏览数据契约与阶段衔接。

Skill文件存在不等于会话已加载，可明确要求Codex读取仓库路径；用户级可安装到~/.codex/skills。调用示例：“使用本仓库food-trend-weekly，直接浏览小红书美食频道，先找5条并保存详情，完成后停止。”

浏览器直找已验证能取得候选及公开互动，但仍可能遇登录、验证、过期链接和模糊日期。脚本不自动浏览，也不保证找全爆款。没有创建定时任务。旧MediaCrawler数据仅作历史兼容，不再作为新采集流程。
