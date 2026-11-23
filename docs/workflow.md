# 工作流程与职责

1. 采集：Codex根据平台说明操作已登录浏览器，读取真实公开字段。`run.py collect`只管理本地日期归档、完整性、去重和进度，不会自行浏览或扫码。
2. 整理：`run.py discovery`检查并冻结已有记录；`run.py screen`按固定规则标准化、判断相关性、去重并生成优先与候补清单。不重新采集，不按视频发布时间过滤。
3. 复查：用户使用viewer打开候选，标记与备注；Codex在需要时看原视频或可靠字幕补充具体内容证据。标记“保留”不等于完成形式核验。
4. 报告：仅有复查标记时调用`review-report`生成明确标记的草稿；拥有完整checks.jsonl时调用`verify`、`report`。两者都使用templates/weekly_report.md的01–06结构，第05节完整明细使用表格。
5. 导出：`run.py export`生成可编辑Word；自动PDF需要LibreOffice。当前本机没有LibreOffice时，可在Word中另存为PDF。交付前检查实际页面和链接，不能把生成DOCX当作排版验收完成。

Skill负责读规则、选择用户授权的阶段、协调浏览器和验收。Python负责固定校验、转换、筛选、计数、文件写入和排版。筛选参数只能在config中调整，Skill不另设临时门槛。

出刊周期、归档日期、实际采集时间、视频发布时间分别记录。三个平台的视频发布时间不限；累计互动不是增长，样本前列不是全平台热榜。

参数：config/collection.json、config/screening.json、config/report.json。字段见[data_format.md](data_format.md)，采集与续采见[collection.md](collection.md)，命令与输出见[usage.md](usage.md)。同一规则只保留对应权威来源。

整个data目录仅留本地，包含原数据、复查文件、运行记录和成稿，不提交GitHub；查看器目录和日期归档格式保持原样。
