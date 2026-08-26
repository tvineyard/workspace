#!/usr/bin/env python3
"""Build a single-file HTML version from the structured project."""
from pathlib import Path
import json, re, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
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
html = html.replace('<link rel="stylesheet" href="assets/styles.css">', '<style>'+css+'</style>')
html = html.replace('<script src="data/rosters.seed.js"></script>', '<script>window.VOL_ROSTERS='+json.dumps(rosters, ensure_ascii=False)+';</script>')
html = html.replace('<script src="src/app.js"></script>', '<script>'+js+'</script>')
out = ROOT/'dist'/'name-a-vol-single.html'
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print(out)
