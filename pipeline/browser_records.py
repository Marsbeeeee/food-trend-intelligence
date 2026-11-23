"""Adapt explicitly observed browser evidence. Never infer dates or missing metrics."""
import hashlib, re
from datetime import datetime
from pipeline.metrics import observe_metrics, parse_display

def approximate_display(value):
    parsed=parse_display(value)
    return parsed is not None and parsed['kind'] in ('approximate','lower_bound')

def completeness_errors(raw, policy):
    """Return reasons only; rejected payloads must not enter a run."""
    r=raw['raw_record']; errors=[]
    if not isinstance(r,dict):return ['not_object']
    displays=r.get('metrics_display',{})
    if not isinstance(displays,dict):return ['invalid_metrics_display']
    for k in ('content_id','url','source_url','title','author','captured_at'):
        if not isinstance(r.get(k),str) or not r[k].strip():errors.append('missing_'+k)
    for k in ('url','source_url'):
        if not isinstance(r.get(k),str) or not r[k].startswith('https://'):errors.append('invalid_'+k)
    for k in ('captured_at',):
        try:
            if datetime.fromisoformat(r.get(k) or '').tzinfo is None:raise ValueError()
        except (TypeError,ValueError):errors.append('invalid_'+k)
    if r.get('published_at'):
        try:
            if datetime.fromisoformat(r['published_at']).tzinfo is None:raise ValueError()
        except (ValueError,TypeError):errors.append('invalid_publication_format')
    if r.get('content_type')!='video':errors.append('not_confirmed_video')
    if r.get('detail_status')!='complete':errors.append('detail_incomplete')
    if r.get('schema')!='browser_video_v1':errors.append('invalid_schema')
    metrics=r.get('metrics')
    if not isinstance(metrics,dict):metrics={}
    required=policy['completeness']['required_metrics'][raw['source_platform']]
    for k in ('views','likes','coins','favorites','shares','comments'):
        if k not in metrics:errors.append('missing_metric_key_'+k)
        v=metrics.get(k)
        if (k in required and v is None and not approximate_display(displays.get(k))) or (v is not None and (type(v) is not int or v<0)):
            errors.append('invalid_metric_'+k)
    try:observe_metrics(metrics,displays)
    except ValueError:errors.append('metric_precision_conflict')
    if r.get('keyword') not in policy['collection']['keywords']:errors.append('invalid_keyword')
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
        "url":r["url"].strip(),"title":re.sub(r'\s+',' ',r.get("title") or '').strip(),"description":r.get("description"),"author_id":r.get("author_id"),"author_name":re.sub(r'\s+',' ',r.get("author") or '').strip().removeprefix('@').strip(),
        "content_type":r.get("content_type","unknown"),"published_at":timestamp(r.get("published_at")),"published_date":r.get('published_date'),"published_date_start":r.get('published_date_start'),"published_date_end":r.get('published_date_end'),
        "published_at_raw":r.get("published_at_display"),"published_at_status":"observed_exact" if r.get("published_at") else "date_only" if r.get('published_date') else "date_range" if r.get('published_date_start') else "unknown",
        "captured_at":timestamp(r["captured_at"]),"metrics":metrics,"metrics_display":r.get("metrics_display",{}),
        "metric_observations":observe_metrics(metrics,r.get("metrics_display",{})),
        "source_keyword":r.get("keyword"),"source_ref":source,"field_provenance":{"method":"direct_browser","source_url":r["source_url"],"published_at_evidence":r.get("published_at_evidence")},
        "search_conditions":r.get('search_conditions',{}),"detail_status":r.get("detail_status","pending")}

