#!/usr/bin/env python3
"""Fetch Tennessee football rosters 1990-2026 from the official UT Athletics roster pages.

Outputs data/rosters.full.json. Uses Jina Reader only as a text-normalization proxy;
the underlying source of truth is utsports.com.
"""
from pathlib import Path
import json, re, time, unicodedata, urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "rosters.full.json"
START_YEAR, END_YEAR = 1990, 2026


def normalize(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("’", "'").strip()
    return re.sub(r"\s+", " ", s)


def clean_name(s):
    s = s.strip()
    s = re.sub(r"^\[([^\]]+)\]\([^)]+\)$", r"\1", s)
    s = s.replace("**", "")
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_roster(markdown):
    names = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if "|" not in line:
            continue
        cells = [x.strip() for x in line.split("|")]
        if len(cells) < 3:
            continue
        jersey = re.sub(r"[*_]", "", cells[0]).strip()
        if not re.fullmatch(r"\d{1,2}", jersey):
            continue
        name = clean_name(cells[1])
        if not name or name.lower() in {"name", "image"} or not re.search(r"[a-z]", name, re.I):
            continue
        if 3 <= len(name) <= 60:
            names.append(name)

    if len(names) < 20:
        for m in re.finditer(r"Full Bio for\s+([^\n\r]+)", markdown, re.I):
            name = clean_name(m.group(1))
            if 3 <= len(name) <= 60:
                names.append(name)

    dedup = {}
    for n in names:
        dedup.setdefault(normalize(n), n)
    return list(dedup.values())


def fetch_year(year):
    target = "https://utsports.com/sports/football/roster" if year == 2026 else f"https://utsports.com/sports/football/roster/{year}"
    reader = "https://r.jina.ai/" + target
    req = urllib.request.Request(reader, headers={"User-Agent": "Name-a-Vol roster builder/1.0", "Accept": "text/plain"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    names = parse_roster(text)
    if len(names) < 20:
        raise RuntimeError(f"{year}: parsed only {len(names)} names")
    return names


def main():
    seed_path = ROOT / "data" / "rosters.seed.json"
    rosters = json.loads(seed_path.read_text()) if seed_path.exists() else {}
    for year in range(START_YEAR, END_YEAR + 1):
        key = str(year)
        if key in rosters and len(rosters[key]) >= 20:
            print(f"{year}: keeping bundled seed ({len(rosters[key])})")
            continue
        try:
            rosters[key] = fetch_year(year)
            print(f"{year}: {len(rosters[key])} players")
        except Exception as exc:
            print(f"{year}: ERROR {exc}")
        OUT.write_text(json.dumps(rosters, indent=2, ensure_ascii=False) + "\n")
        time.sleep(0.7)
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
