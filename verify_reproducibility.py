"""Run four stages twice without crawling; compare content and test resume."""
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--input-root',required=True);a=p.parse_args()
def call(stage,dest,extra=(),ok=True):
    r=subprocess.run([sys.executable,str(ROOT/'run_pipeline.py'),stage,'--run-id','regression','--run-root',str(dest),'--config',str(ROOT/'config/fixture.json'),*extra],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if ok and r.returncode:raise RuntimeError(r.stdout+r.stderr)
    if not ok:assert r.returncode!=0
with tempfile.TemporaryDirectory() as tmp:
    bases=[Path(tmp)/x for x in ('a','b')]
    for dest in bases:
        call('discovery',dest,['--input-root',a.input_root]);call('screen',dest)
        call('screen',dest,ok=False)
        call('verify',dest);call('report',dest)
        assert (dest/'regression/report.md').exists()
    names=['normalized_candidates.jsonl','screened_candidates.jsonl','filter_summary.json','review_queue.jsonl','verified_cases.json','report.md','report_input.json']
    assert all((bases[0]/'regression'/n).read_bytes()==(bases[1]/'regression'/n).read_bytes() for n in names)
    run=bases[0]/'regression'
    queue=[json.loads(x) for x in (run/'review_queue.jsonl').read_text(encoding='utf-8').splitlines()]
    assert queue
    r=queue[0]
    check={'record_id':r['record_id'],'operator':'synthetic-test-only','checked_at':r['captured_at'],'evidence_url':r['url'],'author':'TEST','published_at':r['published_at'],'content_summary':'Synthetic check used only in temporary test','metric':{'name':'likes','value':1,'captured_at':r['captured_at']},'is_video':True,'food_relevant':True,'intelligence_type':'single_video','performance_basis':'Synthetic test, not real evidence'}
    checks=Path(tmp)/'checks.jsonl';checks.write_text(json.dumps(check)+'\n',encoding='utf-8')
    call('verify',bases[0],['--checks',str(checks)]);call('report',bases[0])
    assert len(json.loads((run/'verified_cases.json').read_text(encoding='utf-8'))['cases'])==1
    assert (run/'report_2.md').exists()
    check['intelligence_type']='trend';checks.write_text(json.dumps(check)+'\n',encoding='utf-8')
    call('verify',bases[0],['--checks',str(checks)],ok=False)
    print(json.dumps({'four_stages':'passed','identical_files':len(names),'resume':'passed','invalid_trend':'rejected','synthetic_checks':'temporary only'}))
