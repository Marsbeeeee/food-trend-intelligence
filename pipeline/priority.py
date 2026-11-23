"""Within-platform all-time review priority; cumulative counts, not growth."""
def prioritize(records, policy):
    groups={}
    result={}
    for r in records:
        if r["decision"]!="keep": continue
        groups.setdefault(r["platform"],[]).append(r)
    for platform, cohort in sorted(groups.items()):
        for name in policy["ranking"]["platform_metrics"][platform]:
            available=[r for r in cohort if r["metrics"].get(name) is not None]
            if len(available)<policy["ranking"]["min_cohort"]: continue
            ordered=sorted(available,key=lambda r:(-r["metrics"][name],r["record_id"]))
            for rank,r in enumerate(ordered,1):
                if rank>policy["ranking"]["top_k_per_metric"]: break
                item=result.setdefault(r["record_id"],{"record_id":r["record_id"],"platform":platform,"title":r["title"],"url":r["url"],"metrics":r["metrics"],"publication_scope":"all_time","reasons":[],"status":"review_priority_only"})
                item["reasons"].append({"metric":name,"rank":rank,"cohort_size":len(available),"value":r["metrics"][name]})
    return [result[k] for k in sorted(result)]

