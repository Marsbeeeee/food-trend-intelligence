"""Historical regression policy loader; current accounts use benchmarks.py."""
import json
from pathlib import Path
from pipeline.paths import ROOT
def load_policy(collection=None,screening=None):
    collection=Path(collection) if collection else ROOT/'config/legacy/collection.json'
    screening=Path(screening) if screening else ROOT/'config/legacy/screening.json'
    # Frozen historical configs may name the retired combined source file.
    if not collection.exists() and collection==ROOT/'config/discovery_policy.json':collection=ROOT/'config/legacy/collection.json'
    a=json.loads(collection.read_text(encoding='utf-8'));b=json.loads(screening.read_text(encoding='utf-8'))
    if set(a)&set(b):raise ValueError('Policy sections must have one source')
    return {**a,**b}

