#!/usr/bin/env python3
"""Build a single-file HTML version from the structured project."""
from pathlib import Path
import json, re
ROOT = Path(__file__).resolve().parents[1]
index = (ROOT/'index.html').read_text()
css = (ROOT/'assets'/'styles.css').read_text()
js = (ROOT/'src'/'app.js').read_text()
full = ROOT/'data'/'rosters.full.json'
roster_file = full if full.exists() else ROOT/'data'/'rosters.seed.json'
rosters = json.loads(roster_file.read_text())
html = index
html = html.replace('<link rel="stylesheet" href="assets/styles.css">', '<style>'+css+'</style>')
html = html.replace('<script src="data/rosters.seed.js"></script>', '<script>window.VOL_ROSTERS='+json.dumps(rosters, ensure_ascii=False)+';</script>')
html = html.replace('<script src="src/app.js"></script>', '<script>'+js+'</script>')
out = ROOT/'dist'/'name-a-vol-single.html'
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print(out)
