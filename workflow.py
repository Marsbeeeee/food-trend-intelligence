"""Four stages: direct browser evidence, Python screening, verification, Markdown."""
import argparse, hashlib, json, re
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pipeline.common import food_relevance, canonical_url
from pipeline.browser_records import normalize_browser, completeness_errors
from pipeline.priority import prioritize

ROOT=Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');temp.replace(p)
def save_rows(p,v): p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in v),encoding='utf-8')
def stamp(value):
    d=datetime.fromisoformat(value)
    if d.tzinfo is None: raise ValueError('Timestamp must include timezone')
    return d
def main():
    p=argparse.ArgumentParser()
    p.add_argument('stage',choices=['discovery','screen','verify','report'])
    p.add_argument('--run-id',required=True)
    p.add_argument('--run-root',type=Path,default=ROOT/'data/runs')
    p.add_argument('--config',type=Path,default=ROOT/'config/weekly.json')
    p.add_argument('--input-root',type=Path)
    p.add_argument('--checks',type=Path)
    a=p.parse_args()
    if Path(a.run_id).name!=a.run_id or a.run_id in ('.','..'): p.error('Invalid run ID')
    run=a.run_root/a.run_id
    if a.stage=='discovery':
        if run.exists(): p.error('Run exists; choose a new ID')
        cfg=read(a.config)
        if cfg.get('window_mode')=='rolling_7_days':
            if not cfg.get('observation_cutoff'):p.error('Fix observation_cutoff before browsing')
            anchor=stamp(cfg['observation_cutoff'])
            cfg={**cfg,'observation_cutoff':anchor.isoformat(),'window_end':anchor.isoformat(),'window_start':(anchor-timedelta(days=7)).isoformat()}
            print('Shared collection anchor: '+anchor.isoformat(),flush=True)
        start,end,cutoff=[stamp(cfg[k]) for k in ('window_start','window_end','observation_cutoff')]
        if start>=end or cutoff<start: p.error('Invalid date window')
        policy=read(ROOT/cfg.get('discovery_policy','config/discovery_policy.json'))
        cfg['discovery_description']=str(policy['collection']['platform_routes'])
        if not a.input_root:p.error('--input-root required')
        inputs=[]
        for short,platform in [('xhs','xiaohongshu'),('dy','douyin'),('bili','bilibili')]:
            if short not in cfg.get('platforms',['xhs','dy','bili']):continue
            found=sorted((a.input_root/short).rglob('*.jsonl'))
            if not found:p.error('Missing '+short+' exports; resolve collection first')
            inputs.extend((f,short,platform) for f in found)
        run.mkdir(parents=True);raw=[];discard_reasons={};discarded=0;accepted_counts={};seen_ids=set()
        for i,(f,short,platform) in enumerate(inputs):
            dest=run/'source'/short/f'{i}_{f.name}';dest.parent.mkdir(parents=True,exist_ok=True)
            accepted=[]
            for line in f.read_bytes().splitlines():
                try:
                    record=json.loads(line)
                    if not isinstance(record,dict):raise ValueError('Expected object')
                    reasons=completeness_errors({'source_platform':platform,'raw_record':record},policy)
                    key=(platform,record.get('content_id')) if not reasons else None
                    if not reasons and key in seen_ids:reasons=['duplicate']
                    if not reasons and accepted_counts.get(platform,0)>=policy['collection']['target_complete_per_platform']:reasons=['platform_limit']
                    if reasons:
                        discarded+=1
                        for reason in reasons:discard_reasons[reason]=discard_reasons.get(reason,0)+1
                        continue
                    seen_ids.add(key);accepted_counts[platform]=accepted_counts.get(platform,0)+1;accepted.append(record)
                except (ValueError,UnicodeError,TypeError):
                    discarded+=1;discard_reasons['invalid_record']=discard_reasons.get('invalid_record',0)+1
            save_rows(dest,accepted)
            for n,record in enumerate(accepted,1):
                ref={'file':dest.relative_to(run).as_posix(),'line':n,'sha256':sha(dest)}
                raw.append({'source_platform':platform,'source_ref':ref,'raw_record':record})
        write(run/'discovery_policy.json',policy)
        write(run/'config.json',cfg);save_rows(run/'raw_candidates.jsonl',raw)
        write(run/'discovery.json',{'parsed':len(raw),'accepted_by_platform':accepted_counts,'discarded':discarded,'discard_reasons':discard_reasons,'collection_method':cfg.get('collection_method','direct_browser')})
        output=['config.json','discovery_policy.json','raw_candidates.jsonl','discovery.json']
    else:
        cfg=read(run/'config.json')
        previous={'screen':'discovery','verify':'screen','report':'verify'}[a.stage]
        for name,value in read(run/f'{previous}_manifest.json')['outputs'].items():
            if sha(run/name)!=value:raise SystemExit('Upstream changed: '+name)
        if a.stage=='screen':
            if (run/'screen_manifest.json').exists():raise SystemExit('Already screened; start new run for changed rules')
            normalized=[normalize_browser(r,ZoneInfo(cfg['timezone'])) for r in rows(run/'raw_candidates.jsonl')]
            start,end,cutoff=[stamp(cfg[k]) for k in ('window_start','window_end','observation_cutoff')]
            seen=set();screened=[]
            for r in normalized:
                reasons=[];hard=False
                for k in ('published_at','captured_at'):
                    if not r[k]:reasons.append(k+'_unknown')
                if r['published_at'] and not(start<=stamp(r['published_at'])<end and stamp(r['published_at'])<=cutoff):reasons.append('outside_window');hard=True
                r['observation_age_hours']=(cutoff-stamp(r['published_at'])).total_seconds()/3600
                if r['observation_age_hours']<24:reasons.append('not_mature_24h');hard=True
                if r['content_type']!='video':reasons.append('type_unknown' if r['content_type']=='unknown' else 'not_video');hard|=r['content_type']=='image_text'
                key=(r['platform'],r['content_id'] or canonical_url(r['url']))
                if key[1] and key in seen:reasons.append('duplicate');hard=True
                if key[1]:seen.add(key)
                else:reasons.append('id_unknown')
                if food_relevance(r)!='yes':reasons.append('food_uncertain')
                screened.append({**r,'decision':'exclude' if reasons else 'keep','reason_codes':reasons})
            save_rows(run/'normalized_candidates.jsonl',normalized);save_rows(run/'screened_candidates.jsonl',screened)
            save_rows(run/'excluded.jsonl',[r for r in screened if r['decision']=='exclude'])
            save_rows(run/'review_queue.jsonl',[r for r in screened if r['decision']=='keep'])
            write(run/'filter_summary.json',{'input':len(normalized),'decisions':{x:sum(r['decision']==x for r in screened) for x in ('keep','exclude')}})
            save_rows(run/'priority_queue.jsonl',prioritize(screened,read(run/'discovery_policy.json')))
            output=['priority_queue.jsonl','normalized_candidates.jsonl','screened_candidates.jsonl','excluded.jsonl','review_queue.jsonl','filter_summary.json']
        elif a.stage=='verify':
            candidates={r['record_id']:r for r in rows(run/'review_queue.jsonl')};checks=rows(a.checks) if a.checks else []
            required=['record_id','operator','checked_at','evidence_url','author','published_at','content_summary','metric','is_video','food_relevant','intelligence_type','performance_basis']
            for c in checks:
                if any(not c.get(k) for k in required) or c['record_id'] not in candidates:raise SystemExit('Incomplete or unknown check; see README')
                stamp(c['checked_at']);published=stamp(c['published_at'])
                if not(stamp(cfg['window_start'])<=published<stamp(cfg['window_end']) and published<=stamp(cfg['observation_cutoff'])):raise SystemExit('Verified publication outside window')
                m=c['metric'];stamp(m['captured_at'])
                if m['name'] not in ('views','likes','coins','comments','favorites','shares') or type(m['value']) is not int or m['value']<0:raise SystemExit('Invalid metric')
                if not c['evidence_url'].startswith('https://') or c['is_video'] is not True or c['food_relevant'] is not True:raise SystemExit('Invalid evidence')
                if c['intelligence_type'] not in ('single_video','trend'):raise SystemExit('Invalid intelligence type')
                if c['intelligence_type']=='trend' and len(set(c.get('independent_author_keys',[])))<2:raise SystemExit('Trend requires independent authors')
            if len({c['record_id'] for c in checks})!=len(checks):raise SystemExit('Duplicate checks')
            n=1
            while (run/f'verification_{n}.json').exists():n+=1
            v={'cases':checks,'pending_count':len(candidates)-len(checks),'revision':n}
            write(run/f'verification_{n}.json',v);write(run/'verified_cases.json',v)
            output=['verified_cases.json',f'verification_{n}.json']
        else:
            template=ROOT/cfg.get('template','视频热点情报周报_母版.md');source=template.read_text(encoding='utf-8')
            headings=re.findall(r'^## (0[1-8]｜.+)$',source,re.M)
            if len(headings)!=8:raise SystemExit('Template must contain 01–08')
            cases=read(run/'verified_cases.json')['cases']
            start=stamp(cfg['window_start']).astimezone(ZoneInfo(cfg['timezone']))
            last=stamp(cfg['window_end']).astimezone(ZoneInfo(cfg['timezone']))-timedelta(microseconds=1)
            report_id=f'{start:%Y-%m%d}-{last:%m%d}' if start.year==last.year else f'{start:%Y-%m%d}-{last:%Y-%m%d}'
            source_records={r['record_id']:r for r in rows(run/'review_queue.jsonl')}
            cases=sorted(cases,key=lambda c:c['record_id'])
            cases=[{**c,'entry_id':f'{report_id}-{i:03d}','video_key':source_records[c['record_id']]['platform']+':'+str(source_records[c['record_id']]['content_id'] or canonical_url(source_records[c['record_id']]['url']) or c['record_id'])} for i,c in enumerate(cases,1)]
            parts=['# 视频热点情报周报',f'报告周期：{cfg["window_start"]} 至 {cfg["window_end"]}（结束时刻不含）；观察截止：{cfg["observation_cutoff"]}。']
            parts.insert(1,'周报编号：'+report_id)
            for i,h in enumerate(headings,1):
                parts.append('## '+h)
                if i==1:parts.append(f'经核验情报 {len(cases)} 条（热门单视频 {sum(c["intelligence_type"]=="single_video" for c in cases)}；传播趋势 {sum(c["intelligence_type"]=="trend" for c in cases)}）。采集范围：{cfg["discovery_description"]}。覆盖率未知。')
                elif i in (2,6):parts.extend([f'- [{c["entry_id"]}]({c["evidence_url"]})：{c["content_summary"]}' for c in cases] or ['暂无通过核验的条目。'])
                elif i==3:parts.extend([f'- {c["entry_id"]}：{c.get("form_observation") or "未获取"}' for c in cases] or ['未获取。'])
                elif i==4:
                    for c in cases:
                        m=c['metric'];parts.extend(['### '+c['entry_id'],c['content_summary'],f'作者：{c["author"]}；发布时间：{c["published_at"]}；情报类型：{c["intelligence_type"]}。',f'{m["name"]}：{m["value"]}，采集：{m["captured_at"]}；核验：{c["checked_at"]}。',f'表现依据：{c["performance_basis"]}',f'原视频：{c["evidence_url"]}'])
                elif i==5:parts.append('缺少可比历史快照，跨周变化无法判断。')
                elif i==7:parts.append('仅引用核验记录；单视频与趋势分别计数，不同平台指标不混合排名；未知信息不补数。')
                else:parts.append('状态：待人工审核。目标 20–30 条；不足时按实际数量报告。')
            text='\n\n'.join(parts)+'\n';n=1
            while (run/f'report_{n}.md').exists():n+=1
            (run/f'report_{n}.md').write_text(text,encoding='utf-8');(run/'report.md').write_text(text,encoding='utf-8')
            write(run/'report_input.json',{'report_id':report_id,'cases':cases,'template_sha256':sha(template)})
            (run/f'{report_id}.md').write_text(text,encoding='utf-8')
            output=['report.md',f'report_{n}.md',f'{report_id}.md','report_input.json']
    write(run/f'{a.stage}_manifest.json',{'version':'2.0.0','stage':a.stage,'outputs':{f:sha(run/f) for f in output}})
    print(json.dumps({'stage':a.stage,'run':str(run),'outputs':output},ensure_ascii=False))

if __name__=='__main__':main()

