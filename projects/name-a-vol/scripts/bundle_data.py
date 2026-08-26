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


# Raw roster labels collapse into groups a person would actually name. Hybrids
# ("DL/LB", "P/PK") take their first listed position, which is the primary role.
GROUPS = {
    "football": {
        "QB": "QB", "RB": "RB", "TB": "RB", "FB": "RB", "WR": "WR", "RS": "WR",
        "TE": "TE", "OL": "OL", "OG": "OL", "OT": "OL", "C": "OL",
        "DL": "DL", "DE": "DL", "DT": "DL", "LB": "LB",
        "DB": "DB", "S": "DB", "CB": "DB",
        "PK": "ST", "P": "ST", "LS": "ST", "DS": "ST", "KS": "ST",
        "H": "ST", "K": "ST", "KC": "ST",
    },
    "basketball": {"G": "G", "F": "F", "C": "C"},
}

# What the prompt calls each group, singular and plural.
LABELS = {
    "QB": ["quarterback", "quarterbacks"], "RB": ["running back", "running backs"],
    "WR": ["wide receiver", "wide receivers"], "TE": ["tight end", "tight ends"],
    "OL": ["offensive lineman", "offensive linemen"], "DL": ["defensive lineman", "defensive linemen"],
    "LB": ["linebacker", "linebackers"], "DB": ["defensive back", "defensive backs"],
    "ST": ["kicker or specialist", "kickers and specialists"],
    "G": ["guard", "guards"], "F": ["forward", "forwards"], "C": ["center", "centers"],
}

POSITION_FILES = {"football": "positions.football.json", "basketball": "positions.mens-basketball.json"}


def load_positions(sport, roster):
    """season -> {player name: group}, limited to players actually on the roster."""
    path = ROOT / "data" / POSITION_FILES[sport]
    if not path.exists():
        return {}, {}
    raw = json.loads(path.read_text())
    table = GROUPS[sport]
    out, unmapped = {}, {}
    for season, players in raw.items():
        if season not in roster:
            continue
        got = {}
        for name, label in players.items():
            g = table.get(str(label).split("/")[0].strip().upper())
            if g:
                got[name] = g
            else:
                unmapped[label] = unmapped.get(label, 0) + 1
        if got:
            out[season] = got
    return out, unmapped


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

    positions, labels_used = {}, {}
    for sport in bundle:
        pos, unmapped = load_positions(sport, bundle[sport])
        if pos:
            positions[sport] = pos
            covered = sum(len(v) for v in pos.values())
            total = sum(len(v) for v in bundle[sport].values())
            groups = sorted({g for v in pos.values() for g in v.values()})
            report.append(f"  {sport} positions: {covered}/{total} players, groups {groups}"
                          + (f" UNMAPPED {unmapped}" if unmapped else ""))
            labels_used.update({g: LABELS[g] for g in groups if g in LABELS})

    (ROOT / "data" / "positions.js").write_text(
        "// Player positions by sport and season, collapsed into groups.\n"
        "window.VOL_POSITIONS = " + json.dumps(positions, ensure_ascii=False, sort_keys=True) + ";\n"
        "window.VOL_POSITION_LABELS = " + json.dumps(labels_used, ensure_ascii=False, sort_keys=True) + ";\n")

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
