"""Within-platform, age-banded review priority; never a global hotness score."""
from datetime import datetime
def prioritize(records, policy):
    groups={}
    result={}
    for r in records:
        if r["decision"]!="keep": continue
        if not r.get("published_at") or not r.get("captured_at"): continue
        age=r.get('observation_age_hours')
        if age is None:age=(datetime.fromisoformat(r["captured_at"])-datetime.fromisoformat(r["published_at"])).total_seconds()/3600
        if age<0: continue
        edges=policy["ranking"]["age_bands_hours"]
        band=next((str(e) for e in edges if age<e),"older")
        groups.setdefault((r["platform"],band),[]).append(r)
    for (platform,band), cohort in sorted(groups.items()):
        for name in policy["ranking"]["platform_metrics"][platform]:
            available=[r for r in cohort if r["metrics"].get(name) is not None]
            if len(available)<policy["ranking"]["min_cohort"]: continue
            ordered=sorted(available,key=lambda r:(-r["metrics"][name],r["record_id"]))
            for rank,r in enumerate(ordered,1):
                if rank>policy["ranking"]["top_k_per_metric"]: break
                item=result.setdefault(r["record_id"],{"record_id":r["record_id"],"platform":platform,"title":r["title"],"url":r["url"],"metrics":r["metrics"],"age_band":band,"reasons":[],"status":"review_priority_only"})
                item["reasons"].append({"metric":name,"rank":rank,"cohort_size":len(available),"value":r["metrics"][name]})
    return [result[k] for k in sorted(result)]

