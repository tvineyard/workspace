#!/usr/bin/env python3
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
p = ROOT/'data'/'rosters.full.json'
if not p.exists(): p = ROOT/'data'/'rosters.seed.json'
r = json.loads(p.read_text())
expected = {str(y) for y in range(1990, 2027)}
missing = sorted(expected - set(r))
small = {y: len(v) for y,v in r.items() if len(v) < 20}
print('file:', p.name)
print('seasons:', len(r), '/ 37')
print('players by season:', {y: len(r[y]) for y in sorted(r)})
print('missing:', missing)
print('suspicious (<20 players):', small)
sys.exit(1 if missing or small else 0)
