# 仓库维护规则

以最新确认的用户流程为准。新规则直接替换旧规则，同一规则只保留一个权威来源；确认无调用后删除失效入口与重复文档。不要删除用户数据、母版或无关文件。

统一入口为run.py。业务程序在pipeline/，测试在tests/，母版在templates/。采集关键词、数量与完整性维护在config/collection.json；筛选参数在config/screening.json；出刊编号与运行基准在config/report.json。三个平台的视频发布时间均不限。

字段格式见docs/data_format.md；采集执行见docs/collection.md与docs/collection/；命令见docs/usage.md；职责见docs/workflow.md。Skill只协调现有程序，不临时重写筛选逻辑。

整个data/目录只留本地，被Git忽略；不提交原数据、筛选结果、复查记录、成稿、collection_state或runs。已跟踪的数据从当前分支取消跟踪时保留本地现状，不恢复用户已删除的文件，不清空目录，不重写历史。viewer目录与data日期结构保持原样。

历史运行配置与manifest不能因整理目录被改写。只读解析历史引用是为了继续打开已有run，不保留旧的可执行入口。规则变化使用新run。提交前更新调用、测试和文档链接，运行受影响的离线测试，并用固定样本确认内容ID、筛选结果、标签及互动值一致。Word/PDF导出须检查实际渲染；没有PDF环境时如实说明，不能宣称完成转换。
