"""Synthetic browser contract checks and four-stage integration; no live browsing."""
import json,subprocess,sys,tempfile
from pathlib import Path
from zoneinfo import ZoneInfo
from pipeline.browser_records import normalize_browser
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
    unknown={**record,'content_id':'unknown-date','published_at':None,'published_at_display':'编辑于2天前'}
    (inputs/'records.jsonl').write_text('\n'.join(json.dumps(x) for x in [record,unknown])+'\n',encoding='utf-8')
    cfg=json.loads((ROOT/'config/weekly.json').read_text(encoding='utf-8'))
    cfg.update(window_mode='fixed',timezone='Asia/Shanghai',platforms=['xhs'],collection_method='direct_browser',window_start='2026-11-15T20:00:00+08:00',window_end='2026-11-22T20:00:00+08:00',observation_cutoff='2026-11-22T20:00:00+08:00')
    config=base/'config.json';config.write_text(json.dumps(cfg),encoding='utf-8')
    for stage in ('discovery','screen','verify','report'):
        subprocess.run([sys.executable,str(ROOT/'run_pipeline.py'),stage,'--run-id','test','--run-root',str(base/'runs'),'--config',str(config),'--input-root',str(base/'input')],check=True,capture_output=True)
    result=[json.loads(x) for x in (base/'runs/test/screened_candidates.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [x['decision'] for x in result]==['keep','pending']
    assert (base/'runs/test/report.md').exists()
    subprocess.run([sys.executable,str(ROOT/'verify_reproducibility.py'),'--input-root',str(base/'input'),'--config',str(config)],check=True,capture_output=True)
print('Browser records: complete URL/string ID preserved, missing and approximate metrics checked, uncertain date pending, four stages passed')
