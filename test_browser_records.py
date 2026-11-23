"""Synthetic browser contract checks and four-stage integration; no live browsing."""
import json,subprocess,sys,tempfile
from pathlib import Path
from zoneinfo import ZoneInfo
from pipeline.browser_records import normalize_browser, completeness_errors, publication_decision
from datetime import datetime
ROOT=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
    base=Path(temp);inputs=base/'input/xhs';inputs.mkdir(parents=True)
    record={'schema':'browser_video_v1','content_id':'123456789012345678901234','url':'https://example.com/video?id=1&required_parameter=keep','source_url':'https://example.com/food','title':'美食家常菜','content_type':'video','captured_at':'2026-11-22T20:00:00+08:00','published_at':'2026-11-20T20:00:00+08:00','metrics':{'likes':50,'favorites':None}}
    source={'source_platform':'xiaohongshu','source_ref':{'sha256':'test','line':1},'raw_record':record}
    normalized=normalize_browser(source,ZoneInfo('Asia/Shanghai'))
    assert normalized['url']==record['url'] and normalized['metrics']['favorites'] is None
    assert normalized['content_id']==record['content_id']
    try:
        normalize_browser({**source,'raw_record':{**record,'metrics':{'likes':'1万'}}},ZoneInfo('Asia/Shanghai'))
        raise AssertionError('Approximate metric accepted as exact')
    except ValueError:pass
    record.update(keyword='美食',author='测试作者',published_at_evidence='原页首次发布时间',detail_status='complete',metrics={'views':None,'likes':50,'coins':None,'favorites':20,'comments':0,'shares':None})
    policy=json.loads((ROOT/'config/discovery_policy.json').read_text(encoding='utf-8'))
    source['raw_record']=record
    assert not completeness_errors(source,policy)
    assert 'invalid_keyword' in completeness_errors({**source,'raw_record':{**record,'keyword':None}},policy)
    rounded={**record,'content_id':'rounded-date','published_at':None,'published_date':'2026-11-19','metrics':{**record['metrics'],'likes':None},'metrics_display':{'likes':'1.2万'}}
    assert not completeness_errors({**source,'raw_record':rounded},policy)
    tz=ZoneInfo('Asia/Shanghai')
    start=datetime.fromisoformat('2026-11-15T20:00:00+08:00');end=datetime.fromisoformat('2026-11-22T20:00:00+08:00')
    assert publication_decision(rounded,start,end,end,tz)==(None,'age_uncertain')
    assert publication_decision({**rounded,'published_date':'2026-11-15'},start,end,end,tz)[0]=='outside_or_uncertain_window'
    assert publication_decision({**rounded,'published_date':'2026-11-21'},start,end,end,tz)[0]=='under_or_uncertain_24h'
    assert completeness_errors({**source,'raw_record':{**rounded,'metrics_display':{'likes':'未知'}}},policy)
    assert completeness_errors({**source,'raw_record':{**rounded,'published_at_display':'编辑于11-19'}},policy)
    for platform in ('douyin','bilibili'):
        full={**record,'keyword':'美食','metrics':{k:0 for k in ('views','likes','coins','favorites','comments','shares')}}
        assert not completeness_errors({**source,'source_platform':platform,'raw_record':full},policy)
        full['metrics']['shares']=None
        assert 'invalid_metric_shares' in completeness_errors({**source,'source_platform':platform,'raw_record':full},policy)
    unknown={**record,'content_id':'unknown-date','published_at':None,'published_at_display':'编辑于2天前'}
    (inputs/'records.jsonl').write_text('\n'.join(json.dumps(x) for x in [record,unknown,rounded])+'\n',encoding='utf-8')
    cfg=json.loads((ROOT/'config/weekly.json').read_text(encoding='utf-8'))
    cfg.update(window_mode='fixed',timezone='Asia/Shanghai',platforms=['xhs'],collection_method='direct_browser',window_start='2026-11-15T20:00:00+08:00',window_end='2026-11-22T20:00:00+08:00',observation_cutoff='2026-11-22T20:00:00+08:00')
    config=base/'config.json';config.write_text(json.dumps(cfg),encoding='utf-8')
    for stage in ('discovery','screen','verify','report'):
        subprocess.run([sys.executable,str(ROOT/'run_pipeline.py'),stage,'--run-id','test','--run-root',str(base/'runs'),'--config',str(config),'--input-root',str(base/'input')],check=True,capture_output=True)
    result=[json.loads(x) for x in (base/'runs/test/screened_candidates.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [x['decision'] for x in result]==['keep','keep']
    assert result[1]['age_band']=='age_uncertain' and result[1]['metrics']['likes'] is None
    summary=json.loads((base/'runs/test/discovery.json').read_text(encoding='utf-8'))
    assert summary['parsed']==2 and summary['discard_reasons']['invalid_publication']==1
    assert 'unknown-date' not in (base/'runs/test/raw_candidates.jsonl').read_text(encoding='utf-8')
    assert 'unknown-date' not in next((base/'runs/test/source/xhs').glob('*.jsonl')).read_text(encoding='utf-8')
    assert (base/'runs/test/report.md').exists()
    subprocess.run([sys.executable,str(ROOT/'verify_reproducibility.py'),'--input-root',str(base/'input'),'--config',str(config)],check=True,capture_output=True)
    check={'record_id':result[1]['record_id'],'operator':'synthetic-test','checked_at':'2026-11-22T20:00:00+08:00','evidence_url':record['url'],'author':record['author'],'published_at':None,'published_date':'2026-11-19','content_summary':'美食测试','metric':{'name':'likes','value':None,'display':'1.2万','captured_at':record['captured_at']},'is_video':True,'food_relevant':True,'intelligence_type':'single_video','performance_basis':'Synthetic precision test, not actual evidence'}
    check_path=base/'checks.jsonl';check_path.write_text(json.dumps(check)+'\n',encoding='utf-8')
    for stage in ('verify','report'):
        subprocess.run([sys.executable,str(ROOT/'run_pipeline.py'),stage,'--run-id','test','--run-root',str(base/'runs'),'--checks',str(check_path)],check=True,capture_output=True)
    report=(base/'runs/test/report.md').read_text(encoding='utf-8')
    assert '1.2万（约数/下限）' in report and '发布时间：2026-11-19' in report
print('Browser records: platform completeness gates, zero values, incomplete discard, complete URL/string ID and four stages/reproducibility passed')

