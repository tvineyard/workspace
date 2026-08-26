#!/usr/bin/env python3
"""Bundle every sport's rosters into the single object the page loads.

Reads one JSON per sport and writes data/rosters.seed.js as
window.VOL_ROSTERS = {sport: {season: [names]}}.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

# App sport key -> (data file written by the scraper, minimum roster size that
# counts as a real season). Football rosters run 90-130, basketball 10-19.
SOURCES = {
    "football":   ("rosters.seed.json", 20),
    "basketball": ("rosters.mens-basketball.json", 8),
}


def main():
    bundle, report = {}, []
    for sport, (fname, minimum) in SOURCES.items():
        path = ROOT / "data" / fname
        if not path.exists():
            report.append(f"  {sport}: {fname} missing - skipped")
            continue
        raw = json.loads(path.read_text())
        kept = {y: sorted(v) for y, v in raw.items() if isinstance(v, list) and len(v) >= minimum}
        dropped = sorted(set(raw) - set(kept))
        bundle[sport] = dict(sorted(kept.items()))
        entries = sum(len(v) for v in kept.values())
        uniq = len({n.lower() for v in kept.values() for n in v})
        report.append(f"  {sport}: {len(kept)} seasons, {entries} entries, {uniq} unique players"
                      + (f" (dropped {dropped})" if dropped else ""))

    if not bundle:
        sys.exit("no roster data found")

    (ROOT / "data" / "rosters.seed.js").write_text(
        "// Tennessee rosters bundled into the game, by sport. Sources: UT Athletics\n"
        "// roster pages, cross-checked for football against the public\n"
        "// CollegeFootballData dataset. Nothing is fetched at runtime.\n"
        "window.VOL_ROSTERS = " + json.dumps(bundle, ensure_ascii=False, sort_keys=True) + ";\n")

    print("bundled:")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
