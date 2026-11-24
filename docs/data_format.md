# 当前数据格式

所有真实数据放 data/YYYY/MMDD/benchmarks/，不提交 Git。以下是合成字段示例，不代表真实账号。JSONL 每行一个 JSON 对象；示例多行展示时须压为一行。

## accounts.jsonl

```json
{
  "creator_id": "creator-demo",
  "platform": "instagram",
  "display_name": "示例账号",
  "handle": "example_baker",
  "profile_url": "https://www.instagram.com/example_baker/",
  "source_url": "https://www.instagram.com/explore/search/",
  "discovery_query": "muscular baker",
  "captured_at": "2026-11-24T08:00:00+00:00",
  "followers": null,
  "followers_display": "12.5K",
  "followers_missing_reason": null,
  "fit": "direct",
  "verification": "profile_observed",
  "persona_evidence": "在主页及多条作品中看到的形象，附代表作品链接或观察范围",
  "bread_evidence": "多条面包作品及链接，说明持续性",
  "identity_evidence": null
}
```

| 字段 | 规则 |
| --- | --- |
| creator_id | 人物 ID，单平台可独立编号；多账号共享 ID 时每行都要 identity_evidence |
| platform | instagram／tiktok／youtube |
| handle | 稳定账号标识；YouTube 无 handle 可记录 channel ID，与主页相符 |
| account_id | 程序派生为 platform:handle（去 @、小写），用于选择和视频关联 |
| profile_url | 原平台 HTTPS 主页，非搜索页或单视频 |
| source_url／discovery_query | 实际发现入口与查询，必须可追溯 |
| captured_at | 带时区 ISO 时间，记录实际观察时刻 |
| followers／followers_display | 可见精确值用整数，约数仅写原始显示；不确定就 null 并写缺失原因 |
| fit | direct 直接对标；adjacent 补充参考；unverified 待核实 |
| verification | profile_observed 已查看主页；search_only 仅发现线索 |
| persona_evidence／bread_evidence | 具体依据；未知写未核实的范围，不编造 |
| identity_evidence | 跨平台互链或其他明确身份依据，不能只有用户名相似 |

粉丝量无入选门槛。未看见记 null，不能将缺失当 0。算法保留 exact／approximate／lower_bound／missing 精度。原始观察不被报告计算值覆盖。

## reviews.jsonl

```json
{"account_id":"instagram:example_baker","decision":"selected","reason":"人设与面包内容稳定，适合深入观察","reviewed_at":"2026-11-24T09:00:00+00:00"}
```

每账号最多一条当前选择。decision 为 pending／selected／reserve／rejected；未提供默认为 pending。search_only 不可 selected；先核实并更新观察，保留旧报告快照。选择不意味着已经看完视频。

## videos.jsonl

```json
{
  "account_id": "instagram:example_baker",
  "url": "https://www.instagram.com/reel/DEMO001/",
  "title": "示例面包作品",
  "author_evidence": "原片作者与已入选主页对应",
  "captured_at": "2026-11-24T10:00:00+00:00",
  "published_at": null,
  "format": "short",
  "views": null,
  "views_display": "25K",
  "views_missing_reason": null,
  "baseline_sample": true,
  "sample_reason": "近期连续样本第1条；未按热度挑选",
  "content_group": "unassigned",
  "group_reason": null,
  "content_evidence": null
}
```

format 为 short／long，后者只适用于 YouTube。链接必须为原视频链接，程序从链接派生 content_id 并查重；作者仍需人工核实。发布时间仅在可见时填带时区时间，未知不猜测。

baseline_sample 明确标记是否属于日常基线。历史热门、置顶或例外单独记录理由，不为抬高／压低基线而挑选。content_group 为 ordinary／high／unassigned；前两者要 group_reason，可结合账号历史和基线解释。高表现视频没有统一绝对门槛。

看过原片或可靠字幕后可填 content_evidence：

```json
{"method":"watched","reference":"原视频链接＋00:00–00:08 等观察位置","bread":"制作何种面包","persona":"硬汉形象如何呈现","opening":"开头具体内容","presentation":"镜头、声音和节奏等观察"}
```

method 为 watched／transcript；字幕无法证实画面时直接注明。没有原片／字幕内容依据保留 null。互动指标与内容核实是不同证据。

## 配置、报告与历史记录

init 将三份当前配置冻结进 config_snapshot.json。report／compare 保存四份原输入、report.md 和 SHA-256 manifest；compare 另保存 comparison.json。新版本使用新目录，拒绝覆盖。

旧 data/ 日期结构、旧 run、旧候选 JSONL 和查看器保持原状；不要把新账号数据导入旧查看器。旧格式定义可在 Git 历史查阅，旧合成测试与 config/legacy/ 仅验证历史数据处理能力。

