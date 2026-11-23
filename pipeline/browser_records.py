"""Adapt explicitly observed browser evidence. Never infer dates or missing metrics."""
import hashlib
from datetime import datetime
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
        "content_type":r.get("content_type","unknown"),"published_at":timestamp(r.get("published_at")),
        "published_at_raw":r.get("published_at_display"),"published_at_status":"observed_exact" if r.get("published_at") else "unknown",
        "captured_at":timestamp(r["captured_at"]),"metrics":metrics,"metrics_display":r.get("metrics_display",{}),
        "source_keyword":r.get("keyword"),"source_ref":source,"field_provenance":{"method":"direct_browser","source_url":r["source_url"],"published_at_evidence":r.get("published_at_evidence")},
        "detail_status":r.get("detail_status","pending")}
