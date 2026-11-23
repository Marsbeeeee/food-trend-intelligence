from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.policy import load_policy
"""Offline regression tests; no platform login or live collection."""
