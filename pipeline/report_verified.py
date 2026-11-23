"""Render cases that passed evidence validation using the current master."""
import re
from datetime import timedelta
from zoneinfo import ZoneInfo
from pipeline.paths import template_path
from pipeline.storage import read,write,rows,sha,stamp
from pipeline.links import canonical_url

def report(run,cfg):
    template=template_path(cfg.get('template'));source=template.read_text(encoding='utf-8')
    headings=re.findall(r'^## (0[1-6]｜.+)$',source,re.M)
    if [h[:2] for h in headings]!=[f'{i:02d}' for i in range(1,7)]:raise SystemExit('Template must contain 01–06')
    cases=read(run/'verified_cases.json')['cases']
    start=stamp(cfg['report_period_start']).astimezone(ZoneInfo(cfg['timezone']))
    last=stamp(cfg['report_period_end']).astimezone(ZoneInfo(cfg['timezone']))-timedelta(microseconds=1)
    report_id=f'{start:%Y-%m%d}-{last:%m%d}' if start.year==last.year else f'{start:%Y-%m%d}-{last:%Y-%m%d}'
    source_records={r['record_id']:r for r in rows(run/'review_queue.jsonl')}
    cases=sorted(cases,key=lambda c:c['record_id'])
    cases=[{**c,'entry_id':f'{report_id}-{i:03d}','video_key':source_records[c['record_id']]['platform']+':'+str(source_records[c['record_id']]['content_id'] or canonical_url(source_records[c['record_id']]['url']) or c['record_id'])} for i,c in enumerate(cases,1)]
    parts=['# 视频热点情报周报',f'报告周期：{cfg["report_period_start"]} 至 {cfg["report_period_end"]}（仅为报告编号周期，不限制视频发布日期）；运行基准：{cfg["observation_cutoff"]}。']
    parts.insert(1,'周报编号：'+report_id)
    for i,h in enumerate(headings,1):
        parts.append('## '+h)
        if i==1:parts.append(f'经核验情报 {len(cases)} 条（热门单视频 {sum(c["intelligence_type"]=="single_video" for c in cases)}；传播趋势 {sum(c["intelligence_type"]=="trend" for c in cases)}）。采集范围：{cfg["discovery_description"]}。覆盖率未知。视频发布时间不限，互动为采集时累计值；入选不代表本周新爆款，旧内容可能因累积时间更长而占优。')
        elif i==2:parts.extend([f'- [{c["entry_id"]}]({c["evidence_url"]})：{c["content_summary"]}' for c in cases] or ['暂无通过核验的条目。'])
        elif i==3:parts.extend([f'- {c["entry_id"]}：{c.get("form_observation") or "未获取"}' for c in cases] or ['未获取。'])
        elif i==4:
            for c in cases:
                m=c['metric'];parts.extend(['### '+c['entry_id'],c['content_summary'],f'作者：{c["author"]}；发布时间：{c.get("published_at") or c.get("published_date") or (str(c.get("published_date_start"))+" 至 "+str(c.get("published_date_end")) if c.get("published_date_start") else source_records[c["record_id"]].get("published_at_raw") or "未知")}；情报类型：{c["intelligence_type"]}。',f'{m["name"]}：{m["value"] if m.get("value") is not None else str(m.get("display"))+"（约数/下限）"}，采集：{m["captured_at"]}；核验：{c["checked_at"]}。',f'表现依据：{c["performance_basis"]}',f'原视频：{c["evidence_url"]}'])
        elif i==5:
            escape=lambda value:str(value).replace('|','\\|').replace('\n',' ')
            table=['| 条目 | 作者 | 内容与原视频 | 情报类型 |','| --- | --- | --- | --- |']
            table.extend(f'| {c["entry_id"]} | {escape(c["author"])} | [{escape(c["content_summary"])}]({c["evidence_url"]}) | {c["intelligence_type"]} |' for c in cases)
            parts.append('\n'.join(table))
        elif i==6:parts.append('仅引用核验记录；单视频与趋势分别计数，不同平台指标不混合排名；未知信息不补数。')
    text='\n\n'.join(parts)+'\n';n=1
    while (run/f'report_{n}.md').exists():n+=1
    (run/f'report_{n}.md').write_text(text,encoding='utf-8');(run/'report.md').write_text(text,encoding='utf-8')
    write(run/'report_input.json',{'report_id':report_id,'cases':cases,'template_sha256':sha(template)})
    (run/f'{report_id}.md').write_text(text,encoding='utf-8')
    output=['report.md',f'report_{n}.md',f'{report_id}.md','report_input.json']
    return output
