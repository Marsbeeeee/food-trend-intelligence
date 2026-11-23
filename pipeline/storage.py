"""JSON/JSONL storage, digests and timezone-aware timestamp parsing."""
import json,hashlib
from datetime import datetime
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');temp.replace(p)
def save_rows(p,v): p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in v),encoding='utf-8')
def stamp(value):
    d=datetime.fromisoformat(value)
    if d.tzinfo is None: raise ValueError('Timestamp must include timezone')
    return d
