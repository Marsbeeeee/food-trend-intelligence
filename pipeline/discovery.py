"""Import and freeze complete local browser observations; never collect."""
import json
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from pipeline.paths import ROOT
from pipeline.storage import read,write,rows,save_rows,sha,stamp
from pipeline.policy import load_policy
from pipeline.collection import discover_inputs,record_errors

def discover(a,run,p):
    if run.exists(): p.error('Run exists; choose a new ID')
    cfg=read(a.config)
    if cfg.get('publication_scope')!='all_time':p.error('Use current all_time config; old publication windows are retired')
    anchor=stamp(cfg['observation_cutoff']) if cfg.get('observation_cutoff') else datetime.now(ZoneInfo(cfg['timezone']))
    cfg['observation_cutoff']=anchor.isoformat()
    cfg['report_period_start']=cfg.get('report_period_start') or (anchor-timedelta(days=7)).isoformat()
    cfg['report_period_end']=cfg.get('report_period_end') or anchor.isoformat()
    if stamp(cfg['report_period_start'])>=stamp(cfg['report_period_end']):p.error('Invalid report issue period')
    policy=load_policy(ROOT/cfg.get('collection_policy',cfg.get('discovery_policy','config/collection.json')),ROOT/cfg.get('screening_policy','config/screening.json'))
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
    return output
