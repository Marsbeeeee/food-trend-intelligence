"""Render a review-backed draft without promoting triage marks to verified evidence."""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT=Path(__file__).resolve().parents[1]
PLATFORMS={'bilibili':'B站','douyin':'抖音','xiaohongshu':'小红书'}
METRICS={'views':'播放','likes':'点赞','favorites':'收藏','comments':'评论','coins':'投币','shares':'分享'}

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def load_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def key(row):
    return (row['platform'],row['content_id'])

def snapshots(rows):
    return {key(r):[r['platform'],r['content_id'],r.get('captured_at') or '',r.get('metrics') or {},r.get('metrics_display') or {}] for r in rows}

def validate(rows,review):
    if review.get('schema_version')!='food_review_v1' or not isinstance(review.get('reviews'),list):
        raise ValueError('Invalid review export')
    if any(r.get('platform') not in PLATFORMS or not isinstance(r.get('content_id'),str) for r in rows):
        raise ValueError('Expected normalized candidate rows with string content IDs')
    if len({key(r) for r in rows})!=len(rows):raise ValueError('Duplicate candidates')
    original=json.loads(review['dataset_id'])
    if not isinstance(original,list) or any(not isinstance(r,list) or len(r)!=5 for r in original):raise ValueError('Invalid dataset identity')
    identity={(r[0],r[1]):r for r in original}
    if len(identity)!=len(original) or identity!=snapshots(rows):raise ValueError('Review belongs to another candidate snapshot')
    allowed={key(r) for r in rows};marks={}
    for r in review['reviews']:
        k=tuple(json.loads(r['video_key']))
        if k not in allowed or k in marks or r.get('status') not in ('未复查','保留','淘汰','待确认') or not isinstance(r.get('note'),str):
            raise ValueError('Invalid or duplicate review mark')
        if len(r['note'])>10000:raise ValueError('Review note too long')
        if r.get('updated_at'):
            if datetime.fromisoformat(r['updated_at'].replace('Z','+00:00')).tzinfo is None:raise ValueError('Review time must include timezone')
        marks[k]=r
    return marks

def link(row):
    u=urlsplit(row['url'])
    domains={'douyin':('douyin.com',),'bilibili':('bilibili.com','b23.tv'),'xiaohongshu':('xiaohongshu.com','xhslink.com')}[row['platform']]
    if u.scheme!='https' or u.username or u.password or not any(u.hostname==d or (u.hostname or '').endswith('.'+d) for d in domains):raise ValueError('Unexpected source URL')
    if row['platform']=='douyin':
        modal=parse_qs(u.query,keep_blank_values=True).get('modal_id')
        match=re.fullmatch(r'/video/(\d+)/?',u.path)
        source_id=modal[0] if modal else match[1] if match else None
        if source_id!=row['content_id'] or not re.fullmatch(r'\d{10,25}',row['content_id']):raise ValueError('Douyin URL identity mismatch')
        return 'https://www.douyin.com/video/'+row['content_id']
    return row['url']

def md(text):
    return str(text).replace('\\','\\\\').replace('|','\\|').replace('\n',' ').replace('[','\\[').replace(']','\\]').replace('<','&lt;').replace('>','&gt;')

def counts_text(counts):
    return '；'.join(f'{PLATFORMS[p]} {counts.get(p,0)} 条' for p in PLATFORMS)

def review_label(mark):
    return '已保留；已填写备注' if mark.get('note','').strip() else '已保留；未填写视频形式备注'

def metrics_text(row):
    values=[]
    for k,name in METRICS.items():
        display=(row.get('metrics_display') or {}).get(k)
        exact=(row.get('metrics') or {}).get(k)
        value=display if display not in (None,'') else exact
        if value is not None:values.append(f'{name} {md(value)}')
    return ' · '.join(values)

def build(rows,review,editorial,start,end,generated_on,template):
    marks=validate(rows,review)
    selected=[r for r in rows if marks.get(key(r),{}).get('status')=='保留']
    report_id=f'{start:%Y-%m%d}-{end:%m%d}' if start.year==end.year else f'{start:%Y-%m%d}-{end:%Y-%m%d}'
    annotations=editorial.get('cases',{})
    known={r['platform']+':'+r['content_id'] for r in rows}
    if not set(annotations).issubset(known):raise ValueError('Unknown editorial case')
    headings=re.findall(r'^## (0[1-7]｜.+)$',template,re.M)
    if [h[:2] for h in headings]!=[f'{i:02d}' for i in range(1,8)]:raise ValueError('Template must contain sections 01–07')
    cases=[]
    for i,row in enumerate(selected,1):
        video_key=row['platform']+':'+row['content_id'];annotation=annotations.get(video_key,{})
        if annotation.get('basis','title_description')!='title_description':raise ValueError('This draft renderer accepts title/description editorial observations only')
        cases.append({'entry_id':f'{report_id}-{i:03d}','video_key':video_key,'record':row,'review':marks[key(row)],'annotation':annotation,'url':link(row)})
    by_key={c['video_key']:c for c in cases}
    focus=editorial.get('focus',[])
    if len(focus)>8 or len(set(focus))!=len(focus) or any(k not in by_key for k in focus):raise ValueError('Invalid focus list')
    platform_counts=Counter(c['record']['platform'] for c in cases)
    categories=Counter(c['annotation'].get('category','待细分') for c in cases)
    status_counts=Counter(marks.get(key(r),{}).get('status','未复查') for r in rows)
    captured=[r['captured_at'] for r in rows if r.get('captured_at')]
    times=sorted(captured,key=lambda s:datetime.fromisoformat(s))
    raw_total=editorial.get('source_sample_count','未提供')
    lines=['# 美食高表现视频周报',f'**周报编号：{report_id}**  ',f'报告周期：{start.isoformat()}—{end.isoformat()}（北京时间；出刊编号周期，非视频发布时间范围）  ',f'制作日期：{generated_on}｜归档批次：{md(editorial.get("archive_batch","未填写"))}｜状态：复查后草稿，待成稿审核',
           '> 本期基于已归档的互动快照及用户复查标记整理。视频发布时间不限；“保留”表示用户愿意收录，不等于逐条完成内容形式核验。本文只归纳可追溯的标题、文案与互动数据，不把单次快照称为本周增长或全平台爆款。',
           '## '+headings[0],f'原始样本 **{raw_total} 条** → 同平台多指标筛选 **{len(rows)} 条** → 用户保留 **{len(cases)} 条**。本期按实际保留数量整理，不为满足原母版的20–30条范围而另行删除。',
           counts_text(platform_counts)+'。全部作为高表现单视频候选列示；本期未认定传播趋势，不合并为跨平台热点。',
           f'复查标记：保留 {status_counts["保留"]}；淘汰 {status_counts["淘汰"]}；待确认 {status_counts["待确认"]}；未复查 {status_counts["未复查"]}。本次复查备注 {sum(bool(marks.get(key(r),{}).get("note","")) for r in rows)} 条。',
           '### 本期关键观察']
    for theme in editorial.get('themes',[]):
        evidence=[by_key[k]['entry_id'] for k in theme.get('sources',[]) if k in by_key]
        if not evidence:raise ValueError('Theme needs retained sources')
        lines.append(f'- **{md(theme["title"])}**：{md(theme["observation"])}（依据：'+ '、'.join(evidence)+'）')
    lines.extend(['### 数据范围与限制',f'- 实际采集时间：{times[0] if times else "未记录"} 至 {times[-1] if times else "未记录"}。目录日期是归档标签；以上时间以记录为准，不强制位于报告编号周期内。',
                  '- 三平台均为关键词发现样本；本批实际记录为综合排序。美食、烘焙、美食制作是入口，不代表覆盖整个平台。',
                  '- 互动为采集时累计值，保留“万”等约数与“+”下限；未校正发布时长、曝光量或账号规模。',
                  '- 不同平台不做互动总分或直接排名。原视频链接当前可访问性不由离线脚本保证；抖音按一致的视频ID生成独立页，原搜索弹层地址保留在源数据。',
                  '## '+headings[1],'下列分类用于阅读与选题归纳，不设置分类配额，也不代表已经证实传播趋势。',
                  '| 内容方向 | 本期保留 | 代表案例 |','| --- | ---: | --- |'])
    for category,count in categories.items():
        ids=[c['entry_id'] for c in cases if c['annotation'].get('category','待细分')==category][:3]
        lines.append(f'| {md(category)} | {count} | '+ '、'.join(ids)+' |')
    lines.extend(['## '+headings[2],'### 标题与文案的表达方式','以下是标题或文案中明确出现的表达，不等于已观看并确认镜头、剪辑或声音。'])
    for theme in editorial.get('expressions',[]):
        ids=[by_key[k]['entry_id'] for k in theme['sources'] if k in by_key]
        if not ids:raise ValueError('Expression needs retained sources')
        lines.append(f'- **{md(theme["title"])}**：{md(theme["observation"])}（'+ '、'.join(ids)+'）')
    lines.extend(['### 画面与声音','本次复查记录未填写开头镜头、节奏、构图、ASMR、配乐或转场证据，暂不作具体结论。标题中的“沉浸式”“治愈”等词仅代表创作者的文案表达。',
                  '## '+headings[3],f'以下{len(focus)}条按不同选题方向作编辑选例，并非新增排名，也不代表互动最高的{len(focus)}条。'])
    for k in focus:
        c=by_key[k];r=c['record'];a=c['annotation'];review_mark=c['review']
        lines.extend([f'### {c["entry_id"]}｜{md(a.get("short_title",r["title"]))}',
                      f'**{PLATFORMS[r["platform"]]} · {md(a.get("category","待细分"))} · {md(r.get("priority_label","未分类"))}**',
                      f'**内容线索：**{md(a.get("summary",r["title"]))}',
                      f'**值得观察：**{md(a.get("observation","暂无补充观察。"))}',
                      f'**互动快照：**{metrics_text(r)}。采集于 {r["captured_at"]}。',
                      f'**样本表现依据：**{md("；".join(r.get("selection_reasons",[])))}。',
                      f'**来源：**{md(r.get("author_name","未知"))}｜[打开原视频]({c["url"]})｜发布时间：{md(r.get("published_at") or r.get("published_at_raw") or "未获取")}',
                      f'**复查：**{review_label(review_mark)}。标记时间 {review_mark.get("updated_at") or "未记录"}。'+(f'用户备注：{md(review_mark["note"])}。' if review_mark.get('note','').strip() else '')])
    lines.extend(['## '+headings[4],'缺少另一周同一视频的可比快照，**本期无法判断升温、降温或持续增长**；目录日期和单次搜索结果不能代替跨周证据。',
                  '可在后续同类样本中继续观察：便捷备餐、甜品烘焙的制作门槛表达、地方食物的地域与分量表达。这里只记录观察方向，不安排拍摄或投放任务。',
                  '## '+headings[5],f'以下为用户保留的全部 {len(cases)} 条，共用同一套编号；重点案例是其中的子集。',
                  '| 条目 | 平台 / 作者 | 内容 | 标签与互动快照 | 复查 |','| --- | --- | --- | --- | --- |'])
    for c in cases:
        r=c['record'];a=c['annotation'];title=a.get('short_title') or r['title'].split('#')[0].strip()
        if len(title)>55:title=title[:55]+'…'
        lines.append(f'| {c["entry_id"]} | {PLATFORMS[r["platform"]]} / {md(r.get("author_name","未知"))} | [{md(title)}]({c["url"]}) | {md(r.get("priority_label","未分类"))}；{metrics_text(r)} | {review_label(c["review"])} |')
    lines.extend(['## '+headings[6],
                  '- 原始数据按平台保留；平台与字符串视频ID共同识别内容。筛选结果与复查JSON按数据快照匹配，未改写原数值。',
                  '- 本期正文是“复查后草稿”，不是verify产生的已核验案例。原视频内容核验与具体形式证据仍沿用DATA_FORMAT.md；不为通过脚本而编造checks.jsonl。',
                  '- 只把有两个及以上独立作者、可追溯独立来源且足以支持同一传播模式的材料认定为趋势；本期未作此认定。',
                  '- 采集时显示约数、下限与门槛并列均保留，不把“数据模糊”改成精确值。'])
    payload={'schema_version':'review_report_v1','status':'review_backed_draft','report_id':report_id,'period_start':start.isoformat(),'period_end':end.isoformat(),'generated_on':generated_on,'selected_count':len(cases),'counts_by_platform':dict(platform_counts),'status_counts':dict(status_counts),'cases':cases}
    text='\n\n'.join(lines)+'\n'
    text=re.sub(r'(?<=\|)\n\n(?=\|)','\n',text)
    return text,payload

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidates',type=Path,required=True);p.add_argument('--reviews',type=Path,required=True)
    p.add_argument('--editorial',type=Path,required=True);p.add_argument('--period-start',required=True);p.add_argument('--period-end',required=True)
    p.add_argument('--generated-on',required=True);p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args(argv);start=date.fromisoformat(a.period_start);end=date.fromisoformat(a.period_end);date.fromisoformat(a.generated_on)
    if start>end:p.error('Invalid report period')
    template=ROOT/'视频热点情报周报_母版.md'
    text,payload=build(load_rows(a.candidates),read(a.reviews),read(a.editorial),start,end,a.generated_on,template.read_text(encoding='utf-8'))
    target=a.output_dir/f'美食视频周报_{payload["report_id"]}.md'
    if target.exists():p.error('Report exists; use a new output directory or archive the previous version')
    a.output_dir.mkdir(parents=True,exist_ok=True)
    target.write_text(text,encoding='utf-8',newline='\n')
    (a.output_dir/'report_input.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={'schema_version':'review_report_v1','status':'review_backed_draft','inputs':{str(path):digest(path) for path in (a.candidates,a.reviews,a.editorial,template)},'outputs':{target.name:digest(target),'report_input.json':digest(a.output_dir/'report_input.json')}}
    (a.output_dir/'report_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(target),'selected':payload['selected_count'],'status':payload['status']},ensure_ascii=False))
