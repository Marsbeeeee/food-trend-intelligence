"""Validate supplied human evidence without inventing observations."""
from pipeline.storage import read,write,rows,stamp
from pipeline.normalize import approximate_display

def verify(a,run,cfg):
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
    return output
