"""Four stages: direct browser evidence, Python screening, verification, Markdown."""
import argparse, hashlib, json, re
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pipeline.common import food_relevance, canonical_url
from pipeline.browser_records import normalize_browser, completeness_errors, approximate_display
from pipeline.priority import prioritize
from pipeline.collection import discover_inputs, record_errors

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
        if cfg.get('publication_scope')!='all_time':p.error('Use current all_time config; old publication windows are retired')
        anchor=stamp(cfg['observation_cutoff']) if cfg.get('observation_cutoff') else datetime.now(ZoneInfo(cfg['timezone']))
        cfg['observation_cutoff']=anchor.isoformat()
        cfg['report_period_start']=cfg.get('report_period_start') or (anchor-timedelta(days=7)).isoformat()
        cfg['report_period_end']=cfg.get('report_period_end') or anchor.isoformat()
        if stamp(cfg['report_period_start'])>=stamp(cfg['report_period_end']):p.error('Invalid report issue period')
        policy=read(ROOT/cfg.get('discovery_policy','config/discovery_policy.json'))
        cfg['discovery_description']=str(policy['collection']['platform_routes'])
        if not a.input_root:p.error('--input-root required')
        try:
            inputs=discover_inputs(a.input_root,cfg.get('platforms',['xhs','dy','bili']))
        except ValueError as error:
            p.error(str(error))
        run.mkdir(parents=True);raw=[];discard_reasons={};discarded=0;accepted_counts={};seen_ids=set()
        for i,(f,short,platform) in enumerate(inputs):
            dest=run/'source'/short/f'{i}_{f.name}';dest.parent.mkdir(parents=True,exist_ok=True)
            accepted=[]
            for line in f.read_bytes().splitlines():
                try:
                    record=json.loads(line)
                    if not isinstance(record,dict):raise ValueError('Expected object')
                    reasons=record_errors(record,short,policy)
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
            if 'min_primary_hits' not in read(run/'discovery_policy.json')['ranking']:raise SystemExit('Run uses retired ranking rules; start a new run with the current policy')
            normalized=[normalize_browser(r,ZoneInfo(cfg['timezone'])) for r in rows(run/'raw_candidates.jsonl')]
            seen=set();screened=[]
            for r in normalized:
                reasons=[];hard=False
                if r['content_type']!='video':reasons.append('type_unknown' if r['content_type']=='unknown' else 'not_video');hard|=r['content_type']=='image_text'
                key=(r['platform'],r['content_id'] or canonical_url(r['url']))
                if key[1] and key in seen:reasons.append('duplicate');hard=True
                if key[1]:seen.add(key)
                else:reasons.append('id_unknown');hard=True
                relevance=food_relevance(r)
                if relevance=='no':reasons.append('not_food');hard=True
                elif relevance=='uncertain':reasons.append('food_uncertain')
                screened.append({**r,'food_relevance':relevance,'decision':'exclude' if hard else 'review' if reasons else 'keep','reason_codes':reasons})
            save_rows(run/'normalized_candidates.jsonl',normalized);save_rows(run/'screened_candidates.jsonl',screened)
            save_rows(run/'excluded.jsonl',[r for r in screened if r['decision']=='exclude'])
            save_rows(run/'review_queue.jsonl',[r for r in screened if r['decision']!='exclude'])
            priority=prioritize(screened,read(run/'discovery_policy.json'))
            save_rows(run/'priority_queue.jsonl',priority['selected'])
            save_rows(run/'reserve_candidates.jsonl',priority['reserve'])
            save_rows(run/'needs_review.jsonl',priority['needs_review'])
            write(run/'filter_summary.json',{'input':len(normalized),'decisions':{x:sum(r['decision']==x for r in screened) for x in ('keep','review','exclude')},'priority':priority['summary']})
            lines=['# 清洗与候选筛选结果','','本文件是待核验清单，不是正式周报；累计互动未按发布年龄、曝光量或账号规模校正。',f'输入 {len(normalized)} 条；明确排除 {sum(r["decision"]=="exclude" for r in screened)} 条；相关性待确认 {sum(r["decision"]=="review" for r in screened)} 条。','','| 平台 | 优先核验 | 候补 | 未触发亮点规则 |','| --- | ---: | ---: | ---: |']
            for platform,stats in priority['summary']['platforms'].items():
                lines.append(f'| {platform} | {stats["selected"]} | {stats["reserve"]} | {stats["not_highlighted"]} |')
            lines+=['','## 优先核验条目','']
            for item in priority['selected']:
                lines.append(f'- {item["platform"]} / {item["selection_order"]} [{item["title"]}]({item["url"]}) — '+ '；'.join(item['selection_reasons'])+f'；类别：{item["priority_tier"]}。')
            lines+=['','指标约数只支持粗排；下限值没有精确排名。评论仅作辅助。作者无ID时按名称暂分组，同名情况须核验。未进入优先清单不表示内容没有价值；完整数据与候补仍可追溯。']
            (run/'screen_summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
            output=['priority_queue.jsonl','reserve_candidates.jsonl','needs_review.jsonl','normalized_candidates.jsonl','screened_candidates.jsonl','excluded.jsonl','review_queue.jsonl','filter_summary.json','screen_summary.md']
        elif a.stage=='verify':
            candidates={r['record_id']:r for r in rows(run/'review_queue.jsonl')};checks=rows(a.checks) if a.checks else []
            required=['record_id','operator','checked_at','evidence_url','author','content_summary','metric','is_video','food_relevant','intelligence_type','performance_basis']
            for c in checks:
                if any(not c.get(k) for k in required) or c['record_id'] not in candidates:raise SystemExit('Incomplete or unknown check; see README')
                stamp(c['checked_at'])
                original=candidates[c['record_id']]
                if any(c.get(k)!=original.get(k) for k in ('published_at','published_date','published_date_start','published_date_end')):raise SystemExit('Check publication must match source precision')
                m=c['metric'];stamp(m['captured_at'])
                if m['name'] not in ('views','likes','coins','comments','favorites','shares'):raise SystemExit('Invalid metric')
                if m.get('value') is None:
                    if not approximate_display(m.get('display')):raise SystemExit('Missing metric display')
                elif type(m['value']) is not int or m['value']<0:raise SystemExit('Invalid metric')
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
                elif i in (2,6):parts.extend([f'- [{c["entry_id"]}]({c["evidence_url"]})：{c["content_summary"]}' for c in cases] or ['暂无通过核验的条目。'])
                elif i==3:parts.extend([f'- {c["entry_id"]}：{c.get("form_observation") or "未获取"}' for c in cases] or ['未获取。'])
                elif i==4:
                    for c in cases:
                        m=c['metric'];parts.extend(['### '+c['entry_id'],c['content_summary'],f'作者：{c["author"]}；发布时间：{c.get("published_at") or c.get("published_date") or (str(c.get("published_date_start"))+" 至 "+str(c.get("published_date_end")) if c.get("published_date_start") else source_records[c["record_id"]].get("published_at_raw") or "未知")}；情报类型：{c["intelligence_type"]}。',f'{m["name"]}：{m["value"] if m.get("value") is not None else str(m.get("display"))+"（约数/下限）"}，采集：{m["captured_at"]}；核验：{c["checked_at"]}。',f'表现依据：{c["performance_basis"]}',f'原视频：{c["evidence_url"]}'])
                elif i==5:parts.append('缺少可比历史快照，跨周变化无法判断。')
                elif i==7:parts.append('仅引用核验记录；单视频与趋势分别计数，不同平台指标不混合排名；未知信息不补数。')
                else:parts.append('状态：待人工审核。目标 20–30 条；不足时按实际数量报告。')
            text='\n\n'.join(parts)+'\n';n=1
            while (run/f'report_{n}.md').exists():n+=1
            (run/f'report_{n}.md').write_text(text,encoding='utf-8');(run/'report.md').write_text(text,encoding='utf-8')
            write(run/'report_input.json',{'report_id':report_id,'cases':cases,'template_sha256':sha(template)})
            (run/f'{report_id}.md').write_text(text,encoding='utf-8')
            output=['report.md',f'report_{n}.md',f'{report_id}.md','report_input.json']
    write(run/f'{a.stage}_manifest.json',{'version':'5.0.0','stage':a.stage,'outputs':{f:sha(run/f) for f in output}})
    print(json.dumps({'stage':a.stage,'run':str(run),'outputs':output},ensure_ascii=False))

if __name__=='__main__':main()

