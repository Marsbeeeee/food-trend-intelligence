# 统一数据格式

本地按xhs/、dy/、bili/分别存JSONL，一行一条browser_video_v1。视频身份为平台:原视频ID，ID始终字符串；完整原始快照追加保存，跨run尚不自动归并。

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

核心指标唯一配置见config/discovery_policy.json：小红书点赞/收藏/评论；抖音加分享；B站六项全部。0有效，不能用0补缺；约数不能转成伪精确整数。缺失核心字段补不齐就丢弃，不进入待补池。脚本验证结构不证明链接可访问或证据真实，Codex须实查。

## 可选背景信息
author_id、published_at、published_date、published_date_start/end、published_at_display、published_at_evidence均可为空。能确认首次精确时间就保存带时区published_at；只知道日期就存日期；只知道相对时间或编辑时间就保留展示原文，不伪装首次发布时间。无时间窗口，不为筛选需要推算日期区间；未知日期、编辑日期、旧视频和不足24小时均不构成排除理由。合法的已有日期字段继续保留，不覆盖本地历史数据。

## 核验与输出
checks.jsonl须含record_id（review_queue中）、operator、checked_at、evidence_url、author、content_summary、is_video=true、food_relevant=true、intelligence_type、performance_basis、metric。日期字段可选，但填写时须与源记录精度一致。metric含name/value/captured_at，约数使用value=null、display=原文。intelligence_type为single_video或trend；trend另需至少2个independent_author_keys及独立来源说明。form_observation必须基于原视频或可靠字幕。

discovery.json统计完整条数和丢弃原因；source/只存完整记录；screened_candidates保存去留理由；review_queue只含keep；priority_queue按同平台累计精确指标产生，约数供人工比较；verified_cases保存通过字段检查的核验记录；report_input保留条目编号和视频身份对应。没有发布时间筛选、最低年龄或年龄组。

报告编号周期与视频发布日期范围分离。累计互动不是增长速度，旧视频可能更占优势，不能把本周采到的旧内容写成本周新爆款。
