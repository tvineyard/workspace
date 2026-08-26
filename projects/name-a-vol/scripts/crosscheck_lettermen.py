#!/usr/bin/env python3
"""Compare the all-time lettermen list against the scraped basketball rosters.

Lettermen years are season-ENDING years ("Del Baker 1998" is the 1997-98 season)
while roster data is keyed by the opening year, so 1998 maps to season 1997.

The list only covers players who earned a letter, and only through the article's
2006 date, so it is a floor on each season - anyone here should appear in that
season's roster - not a complete roster.
"""
from pathlib import Path
import json
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower().replace("’", "'")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"[^a-z ]", "", s).replace("  ", " ").strip()


def flip(name):
    """'Baker, Del' -> 'Del Baker'."""
    if "," in name:
        last, first = name.split(",", 1)
        return f"{first.strip()} {last.strip()}".strip()
    return name.strip()


def expand_years(text):
    """'1998, 99, 00, 02' -> [1998, 1999, 2000, 2002]."""
    out, prev = [], None
    for tok in re.findall(r"\d{2,4}", text):
        if len(tok) == 4:
            year = int(tok)
        else:
            if prev is None:
                continue
            year = (prev // 100) * 100 + int(tok)
            while year < prev:
                year += 100
        out.append(year)
        prev = year
    return out


def lev(a, b):
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, dp[0] = dp[0], i
        for j, cb in enumerate(b, 1):
            prev, dp[j] = dp[j], min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
    return dp[-1]


def main():
    lm = json.loads((ROOT / "data" / "lettermen.json").read_text())
    rosters = json.loads((ROOT / "data" / "rosters.mens-basketball.json").read_text())

    # season opening year -> set of normalized letterman names
    by_season = {}
    for e in lm["entries"]:
        who = norm(flip(e["name"]))
        if not who:
            continue
        for end_year in expand_years(e["years"]):
            by_season.setdefault(str(end_year - 1), set()).add(who)

    seasons = sorted(s for s in by_season if s in rosters)
    print(f"lettermen entries: {len(lm['entries'])}; seasons overlapping roster data: {len(seasons)}\n")
    print(f"{'season':8}{'roster':>7}{'letter':>8}{'missing':>9}   names missing from the roster page")
    total_missing, all_missing = 0, {}
    for s in seasons:
        have = {norm(n) for n in rosters[s]}
        want = by_season[s]
        missing = sorted(want - have)
        total_missing += len(missing)
        if missing:
            all_missing[s] = missing
        show = ", ".join(m.title() for m in missing[:4]) + (" …" if len(missing) > 4 else "")
        print(f"{s:8}{len(have):>7}{len(want):>8}{len(missing):>9}   {show}")
    print(f"\ntotal lettermen missing from scraped rosters: {total_missing}")

    if "--merge" in sys.argv:
        # Only add a letterman with no near-match on that roster. Most gaps are
        # spelling differences for someone already present (Alico/Alicio Dunk),
        # and adding those as separate people would corrupt the no-repeat rule.
        added = []
        for e in lm["entries"]:
            who = flip(e["name"])
            k = norm(who)
            for end_year in expand_years(e["years"]):
                season = str(end_year - 1)
                if season not in rosters:
                    continue
                if any(lev(k, norm(n)) <= 3 for n in rosters[season]):
                    continue
                rosters[season] = sorted(set(rosters[season]) | {who})
                added.append(f"{season}: {who}")
        (ROOT / "data" / "rosters.mens-basketball.json").write_text(
            json.dumps(rosters, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        print("\nmerged " + str(len(added)) + " letterman entries the roster pages omit:")
        for a in added:
            print("   " + a)
    (ROOT / "data" / "lettermen-missing.json").write_text(
        json.dumps(all_missing, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
