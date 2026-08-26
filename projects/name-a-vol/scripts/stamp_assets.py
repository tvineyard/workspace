#!/usr/bin/env python3
"""Stamp a content hash onto the asset URLs in index.html.

GitHub Pages lets browsers cache CSS and JS, so an updated index.html can be
served alongside a stale script. When the data shape changes that combination
does not degrade, it crashes - the old script cannot read the new rosters and
the page freezes. Hashing each asset into its query string means a changed file
is always a new URL.
"""
from pathlib import Path
import hashlib
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ["assets/styles.css", "data/rosters.seed.js", "src/app.js"]


def main():
    html = (ROOT / "index.html").read_text()
    for rel in ASSETS:
        path = ROOT / rel
        if not path.exists():
            sys.exit(f"missing asset: {rel}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
        html, n = re.subn(rf'({re.escape(rel)})(\?v=[a-f0-9]+)?"', rf'\1?v={digest}"', html)
        if not n:
            sys.exit(f"{rel} is not referenced by index.html")
        print(f"  {rel} -> v={digest}")
    (ROOT / "index.html").write_text(html)
    print("stamped index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
