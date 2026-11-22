# 美食视频周报：四阶段流程

Skill 指导 Codex 做采集操作、原视频核验及内容判断；Python 负责保存、筛选、校验和组装 Markdown。每一步单独执行，结束后可停下来查看结果。

## 准备

Python 3.11+ 和 Git；Windows 若缺时区数据，安装 `pip install tzdata`。MediaCrawler 是独立外部采集器，需自行准备安装及登录状态。本仓库不保存账号、Cookie、采集数据。

修改 config/weekly.json 的周期、截止时间、关键词和 discovery_description。当前默认值仍是旧样本回归配置，正式运行前必须替换成实际条件。规则在 pipeline/engine.py 的适配函数及 workflow.py 筛选部分；修改规则应更新版本并回归。

## 四步操作

所有命令在仓库根目录运行，以下使用同一个 run ID。

```sh
python run_pipeline.py discovery --run-id weekly-01 --input-root /path/to/exports
python run_pipeline.py screen --run-id weekly-01
python run_pipeline.py verify --run-id weekly-01 --checks /path/to/checks.jsonl
python run_pipeline.py report --run-id weekly-01
```

1. Discovery：Codex 按约定条件调用已有 MediaCrawler，再导入 xhs/、dy/、bili/ 下的 JSONL。可用 `--collector-command` 传 JSON 字符串数组形式的实际命令，配合 `--collector-cwd`；无 shell 拼接。此入口只是调用桥接，不自动推导 MediaCrawler 参数。登录或采集失败先处理；导入旧数据不能称为新采集。保存源文件副本、搜索条件及哈希。
2. Pipeline：统一字段、日期过滤、去重、美食相关性初筛。输出全部决定、排除理由、review_queue.jsonl 和 filter_summary.json。相关性不确定的内容保留待判断。
3. Verification：Codex 优先看高潜力候选原视频，核对原页、热度和内容，写 checks.jsonl。Python 校验记录并保存 verified_cases.json。没有 checks 时可以生成全待核验状态。不会自动访问视频，也不会自动证明人工记录真实。
4. Reporting：Python 读取仓库 MD 母版的 01–08 标题，将已核验的内容描述、形式观察和指标填入报告。它不是完整复制所有母版占位说明；详细条目来自核验记录。输出 report.md，状态为待审核；没有历史数据时跨周判断明确缺失。默认不发布 Google Docs。

结果在 data/runs/<run-id>/。Discovery 和 screen 不覆盖已有结果；补充 checks 后可再次 verify，再 report，保留 verification_N.json 和 report_N.md。变更源数据、配置或筛选规则时创建新 run ID。上一阶段文件被修改会阻止继续运行。

## 核验记录

checks.jsonl 每行一个对象；record_id 来自 review_queue。只填真正完成核验的记录，其他候选保持待核验。三平台统一格式：

```json
{"record_id":"从候选复制","operator":"核验者","checked_at":"2026-11-22T18:00:00+08:00","evidence_url":"https://原视频链接","author":"作者","published_at":"2026-11-20T12:00:00+08:00","content_summary":"有来源支撑的中性内容描述","metric":{"name":"likes","value":123,"captured_at":"2026-11-22T18:00:00+08:00"},"is_video":true,"food_relevant":true,"intelligence_type":"single_video","performance_basis":"说明榜单或同平台对照依据","form_observation":"仅在看过视频或可靠字幕后填写"}
```

示例是格式说明，不是真实证据。metric.name 可为 views/likes/comments/favorites/shares。趋势使用 intelligence_type=trend，并提供至少两个 independent_author_keys；Codex 还必须在 performance_basis 中注明各独立来源与传播依据。脚本只检查结构，不能替代证据核实。无可靠表现依据时不送入正式核验清单。指标核验可以是新时点，旧快照始终保留。

## Skill 与脚本位置

| 文件 | 作用 |
| --- | --- |
| .agents/skills/food-trend-weekly/SKILL.md | Codex 四步操作说明，指导看视频、判断和阶段汇报 |
| run_pipeline.py | 统一命令入口 |
| workflow.py | 四阶段保存、筛选、核验校验、MD 组装 |
| pipeline/engine.py | 复用三平台字段适配；内部旧 main 为历史回归实现，不作为新流程入口 |
| config/weekly.json | 周期和实际采集范围 |
| 视频热点情报周报_母版.md | 报告 01–08 结构来源 |
| verify_reproducibility.py | 四步衔接、重跑一致性与异常测试 |

调用示例：读取本仓库 food-trend-weekly Skill，先执行 Stage 1，完成后给我看采集结果并停止。

Skill 文件存在不等于当前会话已加载；可明确让 Codex 读取该路径。用户级安装目录为 ~/.codex/skills，项目级自动发现由实际客户端验证。

## 测试与限制

`python verify_reproducibility.py --input-root /path/to/exports` 不采集新数据。旧 107 条样本通过四步测试，7 个结果文件两次一致；核验补充后能重新生成报告；重复筛选及证据不足的趋势被拒绝。核验测试使用临时模拟记录，不代表实际完成原帖核验。通用命令不限制输入为 107 条。采集命令桥接尚未用新一轮线上采集验证。

MediaCrawler 开源版声明非商业学习用途；正式商业使用需取得必要授权。此仓库不附带其源码或数据。

## 爆款候选优先级（新增）

采集筛选标准见 COLLECTION_STANDARD.md，参数见 config/discovery_policy.json。screen 额外生成 priority_queue.jsonl：同平台、相近发布时长内，分别按多个指标选前列候选，不计算混合热度分。B站新增 coins，来源为 MediaCrawler video_coin_count；缺失仍为 null。该规则尚未经过新一轮线上采集验证，当前周期配置仍是旧固定样本。

## 编号约定

周报编号采用日期范围，例如 2026-1115-1121；条目采用 2026-1115-1121-001。脚本按配置时区的起始日及结束时刻（不含）之前的日期生成；跨年例为 2026-1227-2027-0102。报告同时输出日期编号文件。report_input.json 保留 entry_id、内部 record_id、video_key 对照；原视频ID不重新编号。补充条目后重新生成的序号可能变化，引用须带对应报告版本；跨批次稳定候选池尚未实现。

## 当前时间口径 V1.2（替代固定周日日期窗口）

正式配置 config/weekly.json 使用 rolling_7_days。以同一北京时间基准时刻 T，发布窗口为 [T−7天,T)，排除采集时不足24小时；分24–72小时和72小时至7天。同一次三平台运行只创建一次 discovery，冻结实际配置后再进行平台采集/导入，或由操作者事先把同一个 T 填入 observation_cutoff；不能为每个平台分别取当前时刻。抖音 ONE_WEEK + MOST_LIKE；B站 MOST_CLICK，显式传同一窗口的时间戳。抖音平台滚动边界可能与 T 略有偏差，导出后再精确筛选并说明缺口。小红书使用最新视频入口，按同一日期口径本地检查，不视为同期热榜。不默认加最新排序补采。周日仅为建议执行日，不是日期范围，也未创建自动任务。

重要：若使用外部 MediaCrawler 先采集再导入，必须先固定 T 并写入配置，随后用它启动两个平台；脚本不能追溯改变已完成采集的搜索条件。默认空 observation_cutoff 在 discovery 启动时生成 T，输出到终端并冻结于运行配置。旧107条测试必须用 config/fixture.json，不使用正式滚动配置。原有固定周日范围的文字均为历史说明，以本节为准。
