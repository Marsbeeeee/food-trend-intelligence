"""Normalize, deduplicate and screen using the frozen policy."""
from zoneinfo import ZoneInfo
from pipeline.normalize import normalize_browser
from pipeline.relevance import food_relevance
from pipeline.links import canonical_url
from pipeline.priority import prioritize,render_summary
from pipeline.storage import read,write,rows,save_rows

def screen(run,cfg):
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
    decisions={x:sum(r['decision']==x for r in screened) for x in ('keep','review','exclude')}
    (run/'screen_summary.md').write_text(render_summary(priority,decisions,len(normalized)),encoding='utf-8')
    output=['priority_queue.jsonl','reserve_candidates.jsonl','needs_review.jsonl','normalized_candidates.jsonl','screened_candidates.jsonl','excluded.jsonl','review_queue.jsonl','filter_summary.json','screen_summary.md']
    return output
