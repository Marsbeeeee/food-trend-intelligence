# food-trend-intelligence

将现有 MediaCrawler JSONL 转成可追溯周报。Python 执行固定规则，Skill 负责调用与检查。没有采集、定时任务或 Google Docs 自动发布功能。

## 运行

Python 3.11+；Windows 如缺少时区数据库，安装 `pip install tzdata`。

把本地固定导出放在任意目录，分别包含 xhs/、dy/、bili/ 下的 JSONL，然后运行：

```sh
python run_pipeline.py --input-root /path/to/exports --run-id 2026-W47-test-01
python verify_reproducibility.py --input-root /path/to/exports
```

报告位于 data/runs/<run-id>/report.md。运行目录存在时拒绝覆盖。config/weekly.json 固定时间窗口和规则版本；本版为 2026-W47 的 107 条固定样本回归，不应直接作为其他周的生产配置。关键词描述历史输入，不会启动新采集。筛选逻辑在 pipeline/engine.py，规则变更须更新版本并回归。

## 目录

```text
.agents/skills/food-trend-weekly/SKILL.md
config/weekly.json
pipeline/engine.py
run_pipeline.py
verify_reproducibility.py
data/runs/                 # 忽略上传，本地生成
```

每次运行保存源文件副本、标准记录、全部筛选决定、排除记录、主题候选、字段核验状态、阶段哈希、日志和 Markdown。report.md 按当前母版 01–08 栏目输出；未观看视频不推断形式，未完成核验不编造热点。现阶段 HTML/PDF/Google Docs 不属于流水线的自动产物。

## Skill 使用

项目内提供 .agents/skills/food-trend-weekly。当前环境的系统创建规范确认用户级发现目录为 ~/.codex/skills；可将 food-trend-weekly 文件夹复制进去后在新会话检查是否出现。项目级目录是否自动加载需由实际客户端确认，不能把文件存在当作加载成功。未安装时可直接让 Codex 读取仓库中的 SKILL.md。

调用示例：使用本仓库 food-trend-weekly Skill，对本地 exports 运行 2026-W47 固定样本测试，生成本地周报。

## 验证结果与边界

107 条真实固定输入两次运行：标准化及筛选均 107 条；日期去重基线小红书 27、抖音 25、B站 10；7 个关键结果文件逐字节一致。未移入旧人工覆写记录，正式案例为 0。历史两条已核验案例不会自动继承；新的核验必须保留操作者、时间和来源。

数据、运行目录、浏览器登录状态、Cookie 和凭据不纳入仓库。此项目复用自有后处理代码，不附带 MediaCrawler 源码。MediaCrawler 开源版声明非商业学习用途，正式商业使用前须取得必要授权。
