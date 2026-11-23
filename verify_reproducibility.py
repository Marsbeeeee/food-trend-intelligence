"""Compare two complete offline runs of browser records; never browse or collect."""
import argparse,subprocess,sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--input-root',required=True);p.add_argument('--config',required=True);a=p.parse_args()
cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
if not cfg.get('observation_cutoff'):p.error('Fix observation_cutoff before reproducibility check')
with tempfile.TemporaryDirectory() as temp:
    runs=[]
    for label in ('a','b'):
        dest=Path(temp)/label
        for stage in ('discovery','screen','verify','report'):
            subprocess.run([sys.executable,str(ROOT/'run_pipeline.py'),stage,'--run-id','comparison','--run-root',str(dest),'--config',a.config,'--input-root',a.input_root],check=True,capture_output=True)
        runs.append(dest/'comparison')
    names=['normalized_candidates.jsonl','screened_candidates.jsonl','filter_summary.json','priority_queue.jsonl','reserve_candidates.jsonl','needs_review.jsonl','review_queue.jsonl','excluded.jsonl','screen_summary.md','verified_cases.json','report.md','report_input.json']
    checks={name:(runs[0]/name).read_bytes()==(runs[1]/name).read_bytes() for name in names}
    if not all(checks.values()):raise SystemExit(str(checks))
    print(json.dumps({'identical':checks}))

