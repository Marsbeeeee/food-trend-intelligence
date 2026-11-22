import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--input-root', required=True)
a = p.parse_args()
root = Path(__file__).resolve().parent
files = ['normalized_candidates.jsonl', 'screened_candidates.jsonl', 'filter_summary.json', 'trend_candidates.json', 'verified_cases.json', 'report.md', 'report_manifest.json']
with tempfile.TemporaryDirectory() as temp:
    paths = []
    for name in ('a', 'b'):
        dest = Path(temp) / name
        subprocess.run([sys.executable, str(root / 'run_pipeline.py'), '--input-root', a.input_root, '--run-root', str(dest), '--run-id', 'regression'], check=True)
        paths.append(dest / 'regression')
    checks = {f: hashlib.sha256((paths[0]/f).read_bytes()).hexdigest() == hashlib.sha256((paths[1]/f).read_bytes()).hexdigest() for f in files}
    assert all(checks.values()), checks
    summary = json.loads((paths[0]/'filter_summary.json').read_text(encoding='utf-8'))
    assert summary['input_rows'] == summary['normalized_rows'] == summary['screened_rows'] == 107
    assert not summary['baseline_differences']
    print(json.dumps({'reproducible': checks, 'rows': 107, 'baseline': summary['baseline_date_dedupe']}, ensure_ascii=False))
