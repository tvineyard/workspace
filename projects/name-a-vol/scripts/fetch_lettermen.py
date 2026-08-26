#!/usr/bin/env python3
"""Fetch the UT men's basketball all-time lettermen article and cross-check it
against the scraped season rosters.

The article is a single historical list, so it is a useful check on seasons whose
roster page looks thin. It only lists players who earned a letter, so it is not a
superset of a roster - walk-ons who never lettered will be absent, and players
after the article's 2006 date will be too.

Writes data/lettermen-raw.txt (cleaned page text, for inspecting the layout) and
data/lettermen.json (whatever the parsers could extract).
"""
from pathlib import Path
import html
import json
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = "https://utsports.com/news/2006/1/10/MEN_S_BASKETBALL_ALL_TIME_LETTERMEN"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


def to_text(doc):
    doc = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", doc, flags=re.S | re.I)
    doc = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", doc, flags=re.I)
    doc = re.sub(r"<[^>]+>", " ", doc)
    doc = html.unescape(doc)
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in doc.splitlines()]
    return "\n".join(ln for ln in lines if ln)


# Candidate shapes for one letterman entry. Each returns (name, years-text).
PATTERNS = {
    "comma_then_years":  re.compile(r"^([A-Z][A-Za-z.'\-]+,\s*[A-Z][A-Za-z.'\- ]+?)\s+((?:'?\d{2,4})[\d\-–,' ]*)$"),
    "name_then_years":   re.compile(r"^([A-Z][A-Za-z.'\- ]+?)\s+((?:19|20)\d{2}\s*[-–]\s*(?:19|20)?\d{2,4})$"),
    "name_paren_years":  re.compile(r"^([A-Z][A-Za-z.'\- ]+?)\s*\(\s*((?:19|20)\d{2}[^)]*)\)$"),
}


def parse(text):
    hits = {k: [] for k in PATTERNS}
    for line in text.splitlines():
        line = line.strip(" .")
        if not (3 < len(line) < 80):
            continue
        for key, pat in PATTERNS.items():
            m = pat.match(line)
            if m:
                hits[key].append({"name": m.group(1).strip(), "years": m.group(2).strip()})
                break
    return hits


def main():
    try:
        doc = fetch(URL)
    except Exception as exc:
        sys.exit(f"fetch failed: {exc}")
    text = to_text(doc)
    (ROOT / "data" / "lettermen-raw.txt").write_text(text[:20000])
    hits = parse(text)
    for k, v in hits.items():
        print(f"{k}: {len(v)} entries", (v[:5] if v else ""))
    best = max(hits, key=lambda k: len(hits[k]))
    (ROOT / "data" / "lettermen.json").write_text(
        json.dumps({"url": URL, "strategy": best, "entries": hits[best],
                    "counts": {k: len(v) for k, v in hits.items()}},
                   indent=2, ensure_ascii=False) + "\n")
    print(f"\npage text: {len(text)} chars; best strategy: {best} ({len(hits[best])})")
    print("\n---- first 60 lines of page text ----")
    for ln in text.splitlines()[:60]:
        print("   ", ln[:110])
    return 0


if __name__ == "__main__":
    sys.exit(main())
