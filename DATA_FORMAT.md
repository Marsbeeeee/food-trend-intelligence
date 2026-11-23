# 本地数据契约

## 浏览记录 browser_video_v1
输入根目录分别使用xhs/、dy/、bili/保存JSONL。配置platforms选择实际导入的平台。每行一个对象：

```json
{"schema":"browser_video_v1","content_id":"原视频ID字符串","url":"https://原视频完整链接及必要参数","source_url":"https://发现入口","title":"页面标题","author":"作者","author_id":null,"content_type":"video","captured_at":"2026-11-22T20:00:00+08:00","published_at":null,"published_at_display":"2天前","published_at_evidence":null,"metrics":{"views":null,"likes":123,"coins":null,"favorites":20,"comments":5,"shares":null},"metrics_display":{"likes":"123"},"detail_status":"partial"}
```

示例不是实际证据。ID必须字符串；完整链接不能去掉必要访问参数。精确时间必须带时区；相对/编辑日期保留原文，不猜首次时间。精确指标只允许非负整数/null，万/10万+放metrics_display。只记录评论总数，不需要抓评论内容。
原始记录追加保存；不要覆盖旧指标。新快照另存，captured_at说明时点。当前跨run尚不自动归并。

## 核验记录 checks.jsonl
每条须含：record_id（来自review_queue）、operator、checked_at、evidence_url、author、published_at（可确认首次发布时间）、content_summary、is_video=true、food_relevant=true、intelligence_type、performance_basis、metric。
metric包含name/value/captured_at；name为views/likes/coins/comments/favorites/shares之一。intelligence_type为single_video或trend，后者还须至少2个independent_author_keys及可追溯的独立来源说明。form_observation可选，必须看过视频或可靠字幕。
没有精确发布时间或可靠表现依据时不要提交为正式checks，保持pending。脚本的字段校验不证明证据真实，Codex必须复核原页。

## 输出
screened_candidates保留每条决定和原因；review_queue包含可继续审查的内容；priority_queue是样本内互动前列，不能直接称爆款。verified_cases保存通过字段检查的核验记录；report_input保留报告条目与视频身份对照。报告仍待人工审核。
