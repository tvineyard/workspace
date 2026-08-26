#!/usr/bin/env python3
"""Merge roster data from any source into the bundled game data, then rebuild.

Usage:
    python scripts/merge_rosters.py incoming.json [more.json ...]

Accepts either shape:
    {"1990": ["Andy Kelly", ...], "1991": [...]}
    {"rosters": {"1990": [...]}}

Names are merged with what is already bundled (union, case/suffix/accent-insensitive),
so re-running is safe and no existing player is ever lost. Rewrites
data/rosters.seed.json, data/rosters.seed.js and data/roster-status.json,
then rebuilds dist/name-a-vol-single.html.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
MIN_PLAYERS = 20


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("’", "'")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"[^a-z ]", "", s).strip()


def load_any(path):
    raw = json.loads(Path(path).read_text())
    if isinstance(raw, dict) and "rosters" in raw and isinstance(raw["rosters"], dict):
        raw = raw["rosters"]
    if not isinstance(raw, dict):
        sys.exit(f"{path}: expected an object mapping year -> [names]")
    out = {}
    for year, names in raw.items():
        y = str(year).strip()
        if not re.fullmatch(r"(19|20)\d{2}", y):
            print(f"  skipping key {year!r}: not a season")
            continue
        if not isinstance(names, list):
            print(f"  skipping {y}: value is not a list")
            continue
        clean = []
        for n in names:
            if isinstance(n, dict):
                n = n.get("name") or f"{n.get('first_name','')} {n.get('last_name','')}"
            n = re.sub(r"\s+", " ", str(n)).strip()
            if len(n) >= 3 and " " in n:
                clean.append(n)
        out[y] = clean
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    seed_path = ROOT / "data" / "rosters.seed.json"
    merged = {}
    for year, names in json.loads(seed_path.read_text()).items():
        merged[year] = {norm(n): n for n in names}
    before = {y: len(v) for y, v in merged.items()}

    for path in sys.argv[1:]:
        print(f"reading {path}")
        for year, names in load_any(path).items():
            bucket = merged.setdefault(year, {})
            for n in names:
                k = norm(n)
                if k:
                    bucket.setdefault(k, n)

    final = {y: sorted(v.values()) for y, v in merged.items() if len(v) >= MIN_PLAYERS}
    dropped = sorted(y for y, v in merged.items() if len(v) < MIN_PLAYERS)
    if dropped:
        print(f"\nignored (fewer than {MIN_PLAYERS} players): {dropped}")

    print(f"\n{'year':6}{'before':>8}{'after':>7}{'new':>6}")
    for y in sorted(final):
        b = before.get(y, 0)
        print(f"{y:6}{b:>8}{len(final[y]):>7}{len(final[y]) - b:>6}")

    seed_path.write_text(json.dumps(final, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    (ROOT / "data" / "rosters.seed.js").write_text(
        "// Tennessee football rosters bundled into the game.\n"
        "window.VOL_ROSTERS = " + json.dumps(final, ensure_ascii=False, sort_keys=True) + ";\n")

    have = sorted(int(y) for y in final)
    missing = [y for y in range(1990, 2027) if y not in have]
    (ROOT / "data" / "roster-status.json").write_text(json.dumps({
        "season_range": [1990, 2026],
        "total_seasons": 37,
        "bundled_seasons": have,
        "bundled_counts": {y: len(final[y]) for y in sorted(final)},
        "not_yet_bundled": missing,
    }, indent=2) + "\n")

    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_single_file.py")], check=True)
    print(f"\nbundled {len(have)}/37 seasons, {sum(len(v) for v in final.values())} player entries")
    print("missing:", missing or "none - all 37 seasons bundled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
