#!/usr/bin/env python3
"""Build a single-file HTML version from the structured project."""
from pathlib import Path
import json, re, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT/'scripts'/'stamp_assets.py')], check=True)
index = (ROOT/'index.html').read_text()
css = (ROOT/'assets'/'styles.css').read_text()
js = (ROOT/'src'/'app.js').read_text()
# The bundled multi-sport object is what the page loads, so rebuild it first and
# embed exactly that - the standalone file can then never drift from the
# structured version.
subprocess.run([sys.executable, str(ROOT/'scripts'/'bundle_data.py')], check=True)
seed_js = (ROOT/'data'/'rosters.seed.js').read_text()
rosters = json.loads(seed_js[seed_js.index('window.VOL_ROSTERS =') + len('window.VOL_ROSTERS ='):].strip().rstrip(';'))
html = index
html = re.sub(r'<link rel="stylesheet" href="assets/styles\.css(?:\?v=[a-f0-9]+)?">', lambda m: '<style>'+css+'</style>', html)
html = re.sub(r'<script src="data/rosters\.seed\.js(?:\?v=[a-f0-9]+)?"></script>', lambda m: '<script>window.VOL_ROSTERS='+json.dumps(rosters, ensure_ascii=False)+';</script>', html)
pos_js = (ROOT/'data'/'positions.js').read_text() if (ROOT/'data'/'positions.js').exists() else ''
html = re.sub(r'<script src="data/positions\.js(?:\?v=[a-f0-9]+)?"></script>', lambda m: '<script>'+pos_js+'</script>', html)
html = re.sub(r'<script src="src/app\.js(?:\?v=[a-f0-9]+)?"></script>', lambda m: '<script>'+js+'</script>', html)
out = ROOT/'dist'/'name-a-vol-single.html'
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print(out)
