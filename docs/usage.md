# 脚本使用说明

## 最常用：清洗一批已采集数据

在仓库根目录运行，使用Python 3.11+。Windows若缺时区数据库，可安装tzdata。下面只导入和整理已有数据，不会打开浏览器或生成正式周报：

```sh
python run.py discovery --run-id 2026-1122-screen-v1 --input-root data/2026/1122
python run.py screen --run-id 2026-1122-screen-v1
```

discovery在这里是“检查并冻结采集文件”，不是重新采集。第一条成功后再运行第二条。下次归档日期为12月5日时，输入目录换成data/2026/1205，run-id也换一个新名称。run-id标识处理批次，正式周报编号仍由config/report.json中的报告周期决定。

同一run不能覆盖导入或筛选。原始数据或规则改变后，换新run-id；不要删除旧结果或修改旧run里冻结的配置。提示“缺少输入”时检查三份文件名，字段错误看discovery.json里的原因，不能补0或编造日期。程序检查链接结构和视频ID是否对应，不会重新打开所有网页证明仍可访问。

## 五个处理模块分别干什么

这些模块由run.py统一调用，不需要逐个运行：

| 文件 | 用途 |
| --- | --- |
| pipeline/normalize.py | 检查字段和数值精度，统一标题空白、作者显示、时间格式、平台和视频身份，保留来源及完整链接 |
| pipeline/metrics.py | 将精确值、约数、下限值分开；例如1.2万得到粗排比较值12000，但原始metrics仍是null；10万+只有下限，没有精确名次 |
| pipeline/relevance.py | 判断美食相关性；明确的贴图烘焙、游戏模组等排除，标题不明确的标为待确认，不直接删除 |
| pipeline/priority.py | 按同平台多项主要指标筛选，使用“多项数据靠前”“一项数据靠前”“数据模糊”三个易读标签，并执行作者与平台数量上限 |
| pipeline/workflow.py | 协调各阶段与校验值；实际处理在对应模块，入口是run.py |

## 当前选例规则

采集和必需字段参数来源为config/collection.json，筛选参数来源为config/screening.json，下面解释当前默认行为，不在脚本外另设规则：

- 同平台分别比较主要指标，至少两项进入前20%的标记为“多项数据靠前”。每项至少有10个可比较观测且存在数值差异才启用粗排；零值不算亮点。评论只作辅助，不能单独触发入选。
- 精确整数和约数展示值参与粗排，约数会明确标记；这是样本内累计表现，没有校正发布年龄、曝光或账号规模，不能称全平台热榜或本周新爆款。
- 名额按可比较样本数乘top_fraction向上取整。门槛同值并列进入候选池，保留并列与精度标记，不伪造精确高低；之后仍执行总量与作者上限。完全相同的指标无法区分强弱，不制造亮点。
- 下限值不参与精确/点值排名。若其已知下限达到可比较样本的粗排门槛，标记为“数据模糊”，作为待确认候选（不是漏采字段）；无论能否进入优先清单，相关记录都保留在needs_review中。下限低于门槛也不证明真实值低。
- 优先“多项数据靠前”，再看“数据模糊”，剩余位置可由“一项数据靠前”补充；候补仍保留自身标签。相关性不确定的记录排在明确相关记录之后，必须先核验。
- 同类别按命中指标数量、最突出指标的样本粗百分位、稳定record_id依次排序；record_id只用于同条件下确定性重放，不表示内容更优秀。不计算跨平台加权总分。
- 每平台最多12条优先核验记录，共最多36条；同作者最多2条。作者优先按ID识别，缺ID时暂按名称分组，可能误合并同名作者，核验时确认。超过上限的亮点保留在候补，不删除源记录。
- 同类选题、跨平台重复内容及借鉴价值留到原视频核验时判断。优先清单不是自动完成核验；草稿按用户实际保留数量整理，正式版按真实核验结果报告，不设硬性条数，不凑数。

## 跑完看哪些文件

输出在data/runs/2026-1122-screen-v1/，不改data/2026/1122/的三份原始文件：

| 文件 | 怎么看 |
| --- | --- |
| screen_summary.md | 先看这份：数量、优先条目、入选原因和限制 |
| normalized_candidates.jsonl | 完整的统一字段及metric_observations派生观测；未进入优先清单也仍在这里 |
| screened_candidates.jsonl | 每条是keep、review还是exclude，以及原因 |
| priority_queue.jsonl | 最多36条优先核验记录；每项命中、粗排名、约数/并列标记都可追溯 |
| reserve_candidates.jsonl | “一项数据靠前”及受作者上限或数量上限影响、未进入优先清单的亮点；not_selected_reason说明原因 |
| needs_review.jsonl | 字段完整但相关性、下限或门槛并列待确认；可以与优先/候补清单重叠，不是新增视频数量 |
| excluded.jsonl | 明确非美食、重复等排除记录及原因 |
| discovery.json、filter_summary.json | 导入丢弃原因、清洗数量、指标精度分布和每平台筛选门槛 |
| review_queue.jsonl | 所有未被明确排除的完整记录，允许核验时从优先清单之外补选 |

核心字段不完整的数据在导入时丢弃，只统计原因；“待确认”清单保留的是字段完整、但内容判断或比较证据需要人工复查的记录，两者不同。运行目录和临时文件默认只留本地。

用户明确要求归档筛选结果时，将优先清单和可读说明复制到指定的data/YYYY/MMDD/目录，按实际候选数命名，例如priority_36.jsonl、priority_36_repo.md；可读文件使用.md扩展名。保留run内部文件名和manifest，不改名或覆盖冻结运行记录。旧run的归档副本可以更新易读标签，筛选依据、条目与数值保持不变；JSONL用priority_label展示中文名称，priority_tier保留稳定机器分类。整个data目录被Git忽略，导出文件和run均只留本地；每次候选数以实际结果为准，不固定写36。

## 采集、核验和报告的其它命令

采集续采步骤见[docs/collection.md](collection.md)，三平台页面说明在docs/collection/。pipeline/collection.py负责按日期保存、校验、去重和进度，不会自行浏览或扫码：

```sh
python run.py collect init --date 2026-12-05
python run.py collect status --date 2026-12-05 --show-ids
python run.py collect audit --date 2026-12-05
```

### 复查后先生成Markdown草稿

只有查看器导出的复查标记、尚未记录具体视频形式证据时，使用review-report，不要补造checks.jsonl。它保留用户“保留”的条目，核对数据快照与原ID，将编辑观察与数据合成01–06结构的“复查后草稿”；不重新筛选，不把标记保留算成完成内容核验。

```sh
python run.py review-report --candidates data/2026/1122/priority_36.jsonl --reviews data/2026/1122/priority_36_review.json --editorial data/2026/1122/report_editorial.json --period-start 2026-11-15 --period-end 2026-11-21 --generated-on 2026-11-22 --output-dir data/runs/2026-1115-1121-review-draft
```

period-end是包含当天的日期，与正式report的内部排他结束时间不同。目录已生成同名报告时会拒绝覆盖，换输出目录保存新版本。输出为美食视频周报_周期.md、report_input.json、report_manifest.json；正式归档时复制到对应日期目录，旧screen run与manifest保持原样。

report_editorial.json由Codex根据现有标题/文案整理：cases按platform:ID填写category、可选short_title/summary/observation，basis必须为title_description；focus列出最多8个保留条目，themes与expressions每项含title、observation、sources。source_sample_count按实际原文件统计，archive_batch填写归档标签。脚本负责校验引用、保留互动精度、组装和计数；编辑观察仍须人工审核。不能把标题描述当作镜头证据，不把相似题材直接升格为传播趋势。
草稿复查栏统一使用“已保留；未填写视频形式备注”（备注为空）或“已保留；已填写备注”（备注非空）。这表示导出记录是否有备注，不表示用户没看视频，也不强制要求补写；仅做选题与互动整理时可不补视频形式。填写普通备注不自动算作完成视频形式核验。

### 具备完整内容证据后生成正式核验版

看过原视频、填好符合[docs/data_format.md](data_format.md)的checks.jsonl后，才进入正式核验与报告：

```sh
python run.py verify --run-id 2026-1122-screen-v1 --checks /local/checks.jsonl
python run.py report --run-id 2026-1122-screen-v1
```

verify只检查已填证据，不会替你看视频；report按现有MD母版组装待审核草稿，不自动发布Google Docs。

## 用查看器复查候选

双击viewer/index.html，用Chrome或Edge打开；不用安装依赖，也不用启动Python。点击“打开候选JSONL”，选择data/2026/1122/priority_36.jsonl；以后换成对应日期的新文件即可。不要在GitHub源码预览页中操作，先同步或下载仓库到本地。

查看器支持平台、中文标签、复查状态和标题/作者/ID搜索；显示采集时的互动快照，保留约数与下限提示，点击链接到原平台看视频。它只展示已有数据，不重新计算排名、不采集、不播放内嵌视频；原平台仍可能要求登录。
抖音“打开原视频”使用独立页https://www.douyin.com/video/视频ID。查看器先核对原地址中的modal_id（优先）或独立页ID与content_id一致，再生成跳转；不使用搜索页中残留的旧/video/ID。原JSONL地址、互动快照和复查文件身份保持不变，完整记录仍可追溯采集时页面。生成地址不表示逐条验证可访问；本次实际打开验证了泡芙样例7616299354227698021，其余只做地址与身份一致性检查。

逐条标记“保留／淘汰／待确认”并写备注。当前浏览器尝试自动暂存；离开前点击“导出复查记录”，得到独立的*_review.json。刷新后可直接点“导入复查记录”选择该文件；若尚未打开候选，会提示打开对应JSONL，载入后自动恢复标记和备注。也可以先打开同一份JSONL，再导入复查记录。误从“打开候选JSONL”选了复查JSON时，查看器也会识别并引导恢复。复查文件只包含标记和备注，不能代替完整候选JSONL；不同批次不混用。导入会替换当前这份数据的全部标记，请先导出备份。换浏览器、移动查看器或清理浏览器数据后，暂存可能不可用，以导出文件为准。

平台与字符串content_id共同识别视频，数据快照独立保存标记，不会把其他日期的复查套到新数据上。查看器不改原始文件或冻结run，不上传文件或备注；导出文件自行保存在本地，不自动提交GitHub。初步复查文件不是verify命令的checks.jsonl，正式核验仍按docs/data_format.md补齐证据。

viewer/core.js负责读取校验与复查文件匹配，app.js负责展示与本地暂存，index.html是入口。离线检查：在仓库根目录运行node viewer/test_core.cjs与node viewer/test_app.cjs（使用当前36条归档测试读取、匹配、筛选、标记和恢复；不替代浏览器视觉检查）。

## 检查脚本是否正常

```sh
python tests/test_metrics.py
python tests/test_priority.py
python tests/test_normalize.py
python tests/test_collection.py
python tests/test_report_draft.py
python tests/check_reproducibility.py --input-root data/2026/1122 --config /local/fixed_config.json
```

核心test脚本分别检查数值精度、多指标选例、完整阶段链路、日期归档续采。tests/check_reproducibility.py会在临时目录执行两次离线流程并比较输出；fixed_config.json按config/report.json结构填写，observation_cutoff必须固定，确保比较基准一致。它生成的临时测试草稿不是正式周报。

完整明细固定使用表格，归入第05节；Word/PDF导出时可单独使用横向页面，跨页重复表头，保留视频链接与全部字段。第06节为核验规则，不再生成跨周观察栏目。

## 统一入口与安装

在仓库根目录使用Python3.11+。推荐在虚拟环境中运行`python -m pip install -e .`；Word导出另运行`python -m pip install -e ".[export]"`。这是仓库内开发工作流，配置与母版随仓库使用。

所有功能从`python run.py`进入：collect、discovery、screen、verify、report、review-report、export、test。`python run.py --help`列出功能，`python run.py collect --help`等显示对应参数。旧的根目录入口已移除，不保留重复命令。

```sh
python run.py test
python run.py export --input data/2026/1122/美食视频周报_2026-1115-1121.md --output-dir data/2026/1122/export-v2 --format docx
# 已安装LibreOffice且soffice在PATH中时可使用 --format both
```

export保留01–06结构和可点击视频链接，第05节使用横向表格并重复表头，按页分段。自动PDF依赖LibreOffice；没有时先导出Word，再由Word另存PDF，不能把未运行的PDF转换称为成功。输出存在时拒绝覆盖，换新目录保存修订。导出后须检查真实页面的中文、分页和链接。

整个data目录被Git忽略；源码拉取不附带样本。Python测试使用合成记录，不依赖本地180条数据。viewer原有测试保持不动，需要本地1122样本时按原命令运行。`tests/check_reproducibility.py`可用于用户明确提供的固定本地样本。

历史run中的discovery_policy.json是当时冻结的合并快照，不是当前参数来源，不移动或改写。程序可只读解析历史配置中的旧母版引用和旧策略路径；新运行使用新config与templates路径。修改规则后始终开新run。
