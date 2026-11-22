"""Synthetic behavior checks; no collection or real verification."""
import json
from pathlib import Path
from pipeline.priority import prioritize
p=json.loads((Path(__file__).parent/'config/discovery_policy.json').read_text(encoding='utf-8'))
records=[{'record_id':str(i),'platform':'bilibili','title':'test','url':'https://example.com','decision':'keep','published_at':'2026-11-20T00:00:00+08:00','captured_at':'2026-11-20T12:00:00+08:00','metrics':{'likes':i,'coins':20-i,'views':None}} for i in range(10)]
out=prioritize(records,p)
assert len(out)==10
assert not prioritize(records[:9],p)
assert not prioritize([{**r,'metrics':{'likes':None}} for r in records],p)
assert all(all(x['metric'] in ('likes','coins') for x in r['reasons']) for r in out)
print('Priority: metric union, small cohorts and null metrics passed')
