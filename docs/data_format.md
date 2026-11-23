# 统一数据格式

原始归档按data/YYYY/MMDD/分别存三份JSONL，一行一条browser_video_v1；文件名由pipeline/collection.py的PLATFORMS定义。归档日期用用户指定日期，未指定时取北京时间当天，一次确定后固定；它不是视频发布日期或报告周期。视频身份为平台:原视频ID，ID始终字符串。同日去重追加并保留第一次完整观测，不同日期分别保留快照，不跨日期删除或覆盖。

三份_original.jsonl是浏览器观测字段的统一封装，尚未经过互动排名和原视频内容核验；不是MediaCrawler导出，也不代表已认定的爆款。进度、尝试日志与冻结配置在data/collection_state/YYYY-MM-DD/，只留本地。操作步骤见docs/collection.md。

## 必需观测
|字段|要求|
|---|---|
|schema|browser_video_v1|
|content_id|原视频ID字符串|
|url|已实际打开成功的完整HTTPS详情链接，保留必要访问参数|
|source_url|实际关键词结果页完整HTTPS链接|
|keyword|实际使用的配置关键词，三个平台都必须填写|
|search_conditions|实际类型、排序；时间条件为不限。不可用或未成功启用的选项如实注明|
|title、author|页面标题、作者名，非空|
|content_type|video，须实际确认|
|captured_at|实际读取指标时刻，ISO格式带时区|
|metrics|六个键views/likes/coins/favorites/comments/shares，精确非负整数或null|
|metrics_display|页面原文；必需指标只有约数时，metrics填null，这里保留如1.2万、10万+|
|detail_status|complete，表示浏览时已核查必需信息|

核心指标唯一配置见config/collection.json：小红书点赞/收藏/评论；抖音加分享；B站六项全部。0有效，不能用0补缺；约数不能转成伪精确整数。缺失核心字段补不齐就丢弃，不进入待补池。脚本验证结构不证明链接可访问或证据真实，Codex须实查。

## 可选背景信息
author_id、published_at、published_date、published_date_start/end、published_at_display、published_at_evidence均可为空。能确认首次精确时间就保存带时区published_at；只知道日期就存日期；只知道相对时间或编辑时间就保留展示原文，不伪装首次发布时间。无时间窗口，不为筛选需要推算日期区间；未知日期、编辑日期、旧视频和不足24小时均不构成排除理由。合法的已有日期字段继续保留，不覆盖本地历史数据。

## 核验与输出

查看器导出的food_review_v1复查JSON仅保存对应快照的用户判断和备注，不等于checks.jsonl。review-report校验其dataset_id与候选的平台/字符串ID/采集时间/原互动字段一致，只收录“保留”，生成review_backed_draft。report_editorial.json是标题与文案的编辑归纳输入，不是观看证据；report_input与manifest保存来源校验、条目映射和草稿状态。复查后草稿与正式核验报告都沿用母版01–06，但分别标明证据成熟度；本期保留数量按实际结果，不设硬性20–30条限制。
checks.jsonl须含record_id（review_queue中）、operator、checked_at、evidence_url、author、content_summary、is_video=true、food_relevant=true、intelligence_type、performance_basis、metric。日期字段可选，但填写时须与源记录精度一致。metric含name/value/captured_at，约数使用value=null、display=原文。intelligence_type为single_video或trend；trend另需至少2个independent_author_keys及独立来源说明。form_observation必须基于原视频或可靠字幕。

discovery.json统计完整条数和丢弃原因；source/只存完整记录。normalized_candidates新增metric_observations：kind为exact/approximate/lower_bound/missing，comparison_value仅用于粗排；lower_bound不填点值排名，原metrics和metrics_display不被派生值覆盖。screened_candidates区分keep/review/exclude并保存原因；review_queue保留keep和review，明确无关的进入excluded。priority_queue按配置生成最多36条多指标优先候选，含primary_hits、metric_evidence、priority_tier、priority_label和selection_reasons。priority_label的中文名称为“多项数据靠前”“数据模糊”“一项数据靠前”，由pipeline/priority.py统一映射；priority_tier只作稳定机器分类；reserve_candidates保存未进优先清单的亮点及原因；needs_review保留字段完整但相关性、下限或门槛并列待确认的记录，可与前两清单重叠。filter_summary统计去留、指标精度、门槛与候选数量，screen_summary.md供直接阅读。verified_cases保存通过字段检查的核验记录；report_input保留条目编号和视频身份对应。没有发布时间筛选、最低年龄或年龄组。详细运行方法见docs/usage.md。

报告编号周期与视频发布日期范围分离。累计互动不是增长速度，旧视频可能更占优势，不能把本周采到的旧内容写成本周新爆款。
