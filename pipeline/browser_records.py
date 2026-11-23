"""Adapt explicitly observed browser evidence. Never infer dates or missing metrics."""
import hashlib, re
from datetime import datetime, timedelta

def approximate_display(value):
    return isinstance(value,str) and re.fullmatch(r'\d+(?:\.\d+)?(?:万|亿|[kKmMwW])\+?|\d+\+',value.strip()) is not None

def publication_bounds(r,tz):
    """Bounds express uncertainty, never a fabricated publication instant."""
    if r.get('published_at'):
        d=datetime.fromisoformat(r['published_at'])
        if d.tzinfo is None:raise ValueError('Publication timezone required')
        return d,d
    d=datetime.strptime(r.get('published_date') or r.get('published_date_start') or '', '%Y-%m-%d').replace(tzinfo=tz)
    last=datetime.strptime(r.get('published_date') or r.get('published_date_end') or '', '%Y-%m-%d').replace(tzinfo=tz)
    if last<d:raise ValueError('Invalid publication range')
    return d,last+timedelta(days=1)-timedelta(microseconds=1)

def publication_decision(r,start,end,cutoff,tz):
    lo,hi=publication_bounds(r,tz)
    if lo<start or hi>=end:return 'outside_or_uncertain_window',None
    youngest=(cutoff-hi).total_seconds()/3600
    oldest=(cutoff-lo).total_seconds()/3600
    if youngest<24:return 'under_or_uncertain_24h',None
    band='24–72h' if oldest<72 else '72h–7d' if youngest>=72 else 'age_uncertain'
    return None,band

def completeness_errors(raw, policy):
    """Return reasons only; rejected payloads must not enter a run."""
    r=raw['raw_record']; errors=[]
    for k in ('content_id','url','source_url','title','author','captured_at','published_at_evidence'):
        if not isinstance(r.get(k),str) or not r[k].strip():errors.append('missing_'+k)
    for k in ('url','source_url'):
        if not isinstance(r.get(k),str) or not r[k].startswith('https://'):errors.append('invalid_'+k)
    for k in ('captured_at',):
        try:
            if datetime.fromisoformat(r.get(k) or '').tzinfo is None:raise ValueError()
        except (TypeError,ValueError):errors.append('invalid_'+k)
    try:
        from zoneinfo import ZoneInfo
        lo,hi=publication_bounds(r,ZoneInfo('Asia/Shanghai'))
        if 'invalid_captured_at' not in errors and lo>datetime.fromisoformat(r['captured_at']):errors.append('publication_after_capture')
    except (ValueError,TypeError):errors.append('invalid_publication')
    if '编辑' in str(r.get('published_at_display','')):errors.append('edited_date_not_publication')
    if r.get('content_type')!='video':errors.append('not_confirmed_video')
    if r.get('detail_status')!='complete':errors.append('detail_incomplete')
    if r.get('schema')!='browser_video_v1':errors.append('invalid_schema')
    metrics=r.get('metrics')
    if not isinstance(metrics,dict):metrics={}
    required=policy['completeness']['required_metrics'][raw['source_platform']]
    for k in ('views','likes','coins','favorites','shares','comments'):
        if k not in metrics:errors.append('missing_metric_key_'+k)
        v=metrics.get(k)
        if (k in required and v is None and not approximate_display(r.get('metrics_display',{}).get(k))) or (v is not None and (type(v) is not int or v<0)):
            errors.append('invalid_metric_'+k)
    if raw['source_platform']!='xiaohongshu' and r.get('keyword') not in policy['collection']['keywords']:errors.append('invalid_keyword')
    return errors
def normalize_browser(raw,tz):
    r=raw["raw_record"];source=raw["source_ref"]
    if r.get("schema")!="browser_video_v1":raise ValueError("Expected browser_video_v1 record")
    for field in ("content_id","url","captured_at","source_url"):
        if not isinstance(r.get(field),str) or not r[field]:raise ValueError("Missing browser field: "+field)
    if not r["url"].startswith("https://"):raise ValueError("Complete HTTPS source link required")
    def timestamp(value):
        if not value:return None
        d=datetime.fromisoformat(value)
        if d.tzinfo is None:raise ValueError("Explicit timestamps require timezone")
        return d.astimezone(tz).isoformat()
    metrics={}
    for k in ("views","likes","coins","favorites","shares","comments"):
        v=r.get("metrics",{}).get(k)
        if v is not None and (type(v) is not int or v<0):raise ValueError("Exact metric must be nonnegative integer or null")
        metrics[k]=v
    content_id=r["content_id"]
    return {"schema_version":"browser_video_v1","record_id":hashlib.sha256(f"{source['sha256']}:{source['line']}".encode()).hexdigest()[:20],
        "platform":raw["source_platform"],"content_id":content_id,"video_key":raw["source_platform"]+":"+content_id,
        "url":r["url"],"title":r.get("title"),"description":r.get("description"),"author_id":r.get("author_id"),"author_name":r.get("author"),
        "content_type":r.get("content_type","unknown"),"published_at":timestamp(r.get("published_at")),"published_date":r.get('published_date'),"published_date_start":r.get('published_date_start'),"published_date_end":r.get('published_date_end'),
        "published_at_raw":r.get("published_at_display"),"published_at_status":"observed_exact" if r.get("published_at") else "date_only" if r.get('published_date') else "date_range" if r.get('published_date_start') else "unknown",
        "captured_at":timestamp(r["captured_at"]),"metrics":metrics,"metrics_display":r.get("metrics_display",{}),
        "source_keyword":r.get("keyword"),"source_ref":source,"field_provenance":{"method":"direct_browser","source_url":r["source_url"],"published_at_evidence":r.get("published_at_evidence")},
        "detail_status":r.get("detail_status","pending")}

