# 操作命令

## 初始化与续采

```sh
python run.py accounts init --date 2026-11-24
```

生成 data/2026/1124/benchmarks/ 下的 config_snapshot.json、accounts.jsonl、reviews.jsonl、videos.jsonl。重复 init 不清空已有记录，也不更新旧配置；新规则用新归档。每个 JSONL 一行一个对象，字段见 [data_format.md](data_format.md)。先读已有记录再补入新观察，重复账号会被验证拒绝，不覆盖第一次观察。

所有命令只处理本地数据。浏览器／搜索工具独立采集并写入 JSONL，不自动调用第三方 API，不使用用户 API Key。

## 候选账号

```sh
python run.py accounts validate --folder data/2026/1124/benchmarks
python run.py accounts report --folder data/2026/1124/benchmarks --output data/runs/2026-1124-accounts-01
```

report 输出 report.md、完整输入快照和 manifest.json。没有选择的账号为 pending，不自动排名。当前流程在此停止。

人工选好后，将 account_id、decision、reason、reviewed_at 写入 reviews.jsonl。decision 可为 selected、reserve、rejected、pending；search_only 不能选入，先核实主页。再次 report 使用新的输出目录。

## 后续视频

```sh
python run.py videos validate --folder data/2026/1124/benchmarks
python run.py videos compare --folder data/2026/1124/benchmarks --output data/runs/2026-1124-compare-01
```

videos.jsonl 只接受 selected 账号。比较按同人物、同平台、同类型分组，以显式 baseline_sample 样本中可比较播放数的中位数为基线。样本不足、全零或没有播放数时不计算倍数；约数保留原始精度，带 + 的下限不参与数值基线。普通与高表现分组来自人工记录，不由程序自动认证。

compare 同时输出 comparison.json 和 Markdown 草稿。每条内容证据缺失就显示“待补”，不生成原因分析。编辑结论需引用视频和证据，提出推断时明确说明。

## 导出与测试

```sh
python -m pip install -e ".[export]"
python run.py export --input data/runs/2026-1124-compare-01/report.md --output-dir data/runs/2026-1124-export-01 --format docx
python run.py test
```

PDF 使用 --format both 并要求 LibreOffice；导出后检查中文、表格、链接和分页。旧模板和旧视频查看器保留，旧 JSONL 不转换、不改写。新账号 JSONL 与旧查看器不兼容，通过 Markdown 表格复查。

历史 collect、discovery、screen、verify、report、review-report 命令已从 run.py 退役。旧模块及 config/legacy/ 只供回归测试解释旧记录，不能用于新采集。

