"""Coordinate frozen stages; implementation lives in stage modules."""
import argparse,json
from pathlib import Path
from pipeline.paths import ROOT
from pipeline.storage import read,write,sha
from pipeline.discovery import discover
from pipeline.screening import screen
from pipeline.verification import verify
from pipeline.report_verified import report
def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('stage',choices=['discovery','screen','verify','report'])
    p.add_argument('--run-id',required=True)
    p.add_argument('--run-root',type=Path,default=ROOT/'data/runs')
    p.add_argument('--config',type=Path,default=ROOT/'config/report.json')
    p.add_argument('--input-root',type=Path);p.add_argument('--checks',type=Path)
    a=p.parse_args(argv)
    if Path(a.run_id).name!=a.run_id or a.run_id in ('.','..'):p.error('Invalid run ID')
    run=a.run_root/a.run_id
    if a.stage=='discovery':output=discover(a,run,p)
    else:
        cfg=read(run/'config.json');previous={'screen':'discovery','verify':'screen','report':'verify'}[a.stage]
        for name,value in read(run/f'{previous}_manifest.json')['outputs'].items():
            if sha(run/name)!=value:raise SystemExit('Upstream changed: '+name)
        output=screen(run,cfg) if a.stage=='screen' else verify(a,run,cfg) if a.stage=='verify' else report(run,cfg)
    write(run/f'{a.stage}_manifest.json',{'version':'5.0.0','stage':a.stage,'outputs':{f:sha(run/f) for f in output}})
    print(json.dumps({'stage':a.stage,'run':str(run),'outputs':output},ensure_ascii=False))
