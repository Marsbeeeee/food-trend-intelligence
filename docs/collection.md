# 海外对标账号采集

## 发现账号

按当前 config/collection.json 的平台顺序搜索。关键词只是发现线索，可按当地语言、人物描述、bread／sourdough／bakery 等词扩展，并记录实际查询。不设账号或平台配额，不为了凑数放宽匹配条件。

优先找同一人物持续呈现硬汉、肌肉、健身、粗犷等形象且持续做面包的账号。不要凭男性身份、纹身或单条面包作品直接判定。用主页和多条内容提供人设与面包依据；纯甜品、泛做饭、品牌转载或偶发烘焙标 adjacent 或 unverified，不混入直接对标。

可以先用公开搜索发现线索，再访问平台主页核实。记录 source_url、discovery_query、captured_at 与核实状态。遇到登录、验证码或限制时如实记录；search_only 候选可留在清单里，后续核实后才能选中。不要把索引摘要当成已观看作品。粉丝量缺失用 null 和原因，不丢弃、不补零。

跨平台同人使用 creator_id 关联，每个平台仍单独一行；需有主页互链、官网互链或其他明确身份依据。相似名称只能作为线索，不能自动合并。

## 交付与停止

更新 accounts.jsonl，运行 accounts validate 和 accounts report，交付候选清单后停止。保留 direct／adjacent／unverified 的区别；粉丝多但近期播放低也可以作为研究对象。未执行视频分析时不要给出视频爆款原因。

## 选人之后

仅在用户要求视频阶段后采入选账号。先确定采样范围并记录 sample_reason，建议先取近期连续作品作为基线，再另外补历史高表现视频。不要只从热门排序取样。置顶、近期刚发、合作、抽奖、转载、广告和内容转型等情况写入采样理由；必要时排除基线但保留该视频。

每条记录原链接、作者依据、发布时间（可见才填）、指标原始显示和快照时间。YouTube Shorts 与长视频分组。每条可另标 ordinary／high／unassigned；分组必须说明相对账号自身的依据，不设统一爆款门槛。

观看原视频或读取可靠字幕后再记录内容证据，转录没有外观或镜头信息时明确写“字幕无法核实”，不能编造人设和画面。只有标题、封面或摘要时，不填 content_evidence。不得从单次累计快照推断增长速度或因果。

平台提示：[Instagram](collection/instagram.md) · [TikTok](collection/tiktok.md) · [YouTube](collection/youtube.md)。

