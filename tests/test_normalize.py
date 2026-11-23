from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.policy import load_policy
"""All-time collection regression, completeness, reporting and reproducibility."""
import json,subprocess,sys,tempfile
from pathlib import Path
from zoneinfo import ZoneInfo
from pipeline.normalize import normalize_browser, completeness_errors
from pipeline.relevance import food_relevance
ROOT=Path(__file__).resolve().parents[1]
policy=load_policy()
for title in ('海鲜自助与便当','三明治和曲奇','收藏这份巴斯克做法'):
    assert food_relevance({'title':title})=='yes'
assert food_relevance({'title':'Blender烘焙贴图教程'})=='no'
assert food_relevance({'title':'今天的快乐'})=='uncertain'
base_record={'schema':'browser_video_v1','keyword':'美食','content_id':'123456789012345678901234','url':'https://www.xiaohongshu.com/explore/123456789012345678901234?required_parameter=keep','source_url':'https://www.xiaohongshu.com/search_result?keyword=food','title':'美食制作','author':'测试作者','content_type':'video','captured_at':'2026-11-22T20:00:00+08:00','detail_status':'complete','metrics':{'views':None,'likes':50,'coins':None,'favorites':20,'comments':0,'shares':None},'search_conditions':{'sort':'综合','date_filter':'不限'}}
def wrap(record,platform='xiaohongshu'):
    return {'source_platform':platform,'raw_record':record,'source_ref':{'sha256':'test','line':1}}
for platform in ('xiaohongshu','douyin','bilibili'):
    full={**base_record,'metrics':{k:0 for k in ('views','likes','coins','favorites','comments','shares')}}
    assert not completeness_errors(wrap(full,platform),policy)
    broken={**full,'metrics':{**full['metrics'],'comments':None}}
    assert 'invalid_metric_comments' in completeness_errors(wrap(broken,platform),policy)
assert 'invalid_keyword' in completeness_errors(wrap({**base_record,'keyword':None}),policy)
normal=normalize_browser(wrap(base_record),ZoneInfo('Asia/Shanghai'))
assert normal['url']==base_record['url'] and normal['content_id']==base_record['content_id']
assert normal['search_conditions']==base_record['search_conditions']
old={**base_record,'content_id':'old','published_at':'2020-01-01T00:00:00+08:00'}
young={**base_record,'content_id':'young','published_at':'2026-11-22T19:00:00+08:00'}
unknown={**base_record,'content_id':'unknown','published_at_display':'编辑于2天前'}
rounded={**base_record,'content_id':'rounded','metrics':{**base_record['metrics'],'likes':None},'metrics_display':{'likes':'1.2万'}}
invalid={**base_record,'content_id':'incomplete','metrics':{**base_record['metrics'],'favorites':None}}
ambiguous={**base_record,'content_id':'ambiguous','title':'今天的快乐'}
irrelevant={**base_record,'content_id':'irrelevant','title':'Blender烘焙贴图教程'}
for item in (old,young,unknown,rounded,invalid,ambiguous,irrelevant):
    item['url']='https://www.xiaohongshu.com/explore/'+item['content_id']+'?required_parameter=keep'
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);folder=root/'input/xhs';folder.mkdir(parents=True)
    (folder/'records.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in (old,young,unknown,rounded,invalid,ambiguous,irrelevant)),encoding='utf-8')
    cfg=json.loads((ROOT/'config/report.json').read_text(encoding='utf-8'))
    cfg.update(platforms=['xhs'],observation_cutoff='2026-11-22T20:00:00+08:00',report_period_start='2026-11-15T00:00:00+08:00',report_period_end='2026-11-22T00:00:00+08:00')
    config=root/'config.json';config.write_text(json.dumps(cfg),encoding='utf-8')
    def run(stage,extra=()):
        subprocess.run([sys.executable,str(ROOT/'run.py'),stage,'--run-id','test','--run-root',str(root/'runs'),'--config',str(config),'--input-root',str(root/'input'),*extra],check=True,capture_output=True)
    for stage in ('discovery','screen','verify','report'):run(stage)
    path=root/'runs/test'
    result=[json.loads(x) for x in (path/'screened_candidates.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(result)==6
    assert {x['content_id'] for x in result if x['decision']=='keep'}=={'old','young','unknown','rounded'}
    assert next(x for x in result if x['content_id']=='ambiguous')['decision']=='review'
    assert next(x for x in result if x['content_id']=='irrelevant')['decision']=='exclude'
    pending=[json.loads(x) for x in (path/'needs_review.jsonl').read_text(encoding='utf-8').splitlines()]
    assert any(x['content_id']=='ambiguous' for x in pending)
    assert all('age_band' not in x for x in result)
    summary=json.loads((path/'discovery.json').read_text(encoding='utf-8'))
    assert summary['parsed']==6 and summary['discarded']==1
    assert 'incomplete' not in (path/'raw_candidates.jsonl').read_text(encoding='utf-8')
    checks=[]
    for item in (row for row in result if row['decision']!='exclude'):
        c={'record_id':item['record_id'],'operator':'synthetic-test','checked_at':base_record['captured_at'],'evidence_url':item['url'],'author':base_record['author'],'content_summary':'美食测试','metric':{'name':'likes','value':item['metrics']['likes'],'display':item['metrics_display'].get('likes'),'captured_at':base_record['captured_at']},'is_video':True,'food_relevant':True,'intelligence_type':'single_video','performance_basis':'Synthetic cumulative-count test only'}
        for k in ('published_at','published_date','published_date_start','published_date_end'):c[k]=item.get(k)
        checks.append(c)
    check_path=root/'checks.jsonl';check_path.write_text(''.join(json.dumps(c)+'\n' for c in checks),encoding='utf-8')
    run('verify',('--checks',str(check_path)));run('report')
    report=(path/'report.md').read_text(encoding='utf-8')
    assert '2020-01-01' in report and '编辑于2天前' in report and '1.2万（约数/下限）' in report
    assert '不限制视频发布日期' in report and '不代表本周新爆款' in report
    subprocess.run([sys.executable,str(ROOT/'tests/check_reproducibility.py'),'--input-root',str(root/'input'),'--config',str(config)],check=True,capture_output=True)
print('PASS: old, under-24h, unknown/edited dates kept; core omissions rejected; full reporting and reproducibility')

