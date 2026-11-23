# 统一数据格式

## 文件与身份
本地输入按xhs/、dy/、bili/分目录保存JSONL，一行一条。目录分别映射xiaohongshu、douyin、bilibili；所有平台使用browser_video_v1。视频身份为平台:原视频ID，ID必须字符串。原始完整快照追加保存，不能覆盖旧互动值；跨run尚不自动归并。

## 完整记录字段
|字段|要求|
|---|---|
|schema|browser_video_v1|
|content_id|原视频ID字符串|
|url|实际打开成功的完整HTTPS详情链接，保留必要访问参数|
|source_url|实际发现入口的完整HTTPS链接|
|keyword|抖音/B站为配置关键词；小红书频道为null|
|title、author|非空页面标题、作者名|
|author_id|可选字符串，不能确认则null|
|content_type|video，须实际确认|
|published_at|首次发布的精确ISO时间，带时区|
|published_at_evidence|证明首次发布时间的页面原文/证据说明，非空|
|published_at_display|页面日期展示原文，可选|
|captured_at|实际读取指标的精确ISO时间，带时区|
|metrics|必须包含views、likes、coins、favorites、comments、shares六个键|
|metrics_display|可选，保存页面展示原文，不能替代必需精确指标|
|detail_status|complete，表示浏览时已人工核查以上内容|

必需指标由config/discovery_policy.json统一定义：小红书点赞/收藏/评论；抖音再加分享；B站六项全部。必需项必须是非负整数（0有效），不得缺失或只填约数；非必需项不能取得则null，不能用0补缺。1.2万、10万+不能转换成伪精确整数。相对/编辑日期不能猜成首次发布时间。脚本验证结构，链接能否打开及证据是否真实仍由Codex实查。

缺项先补全，无法补全就丢弃，不进入正式输入或候选队列。导入遇到旧的不完整记录只累计discard_reasons，不把该记录复制进run。原有用户本地文件不自动删除。

## 核验记录 checks.jsonl
每条须含record_id（review_queue中）、operator、checked_at、evidence_url、author、published_at、content_summary、is_video=true、food_relevant=true、intelligence_type、performance_basis、metric。metric含name/value/captured_at，name为六项指标之一。intelligence_type为single_video或trend，后者至少2个independent_author_keys及独立来源说明。form_observation须基于原视频或可靠字幕。核验不能编造缺失事实。

## 输出
discovery.json给完整条数和丢弃原因汇总；source/只存通过完整性检查的记录。screened_candidates保存完整记录的去留理由；review_queue只含keep；priority_queue是样本内互动优先级；verified_cases为通过字段检查的核验记录；report_input保留条目编号和视频身份对应关系。完整数据不代表已被证实为爆款。
