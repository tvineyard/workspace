#!/usr/bin/env python3
"""Fetch Tennessee football rosters 1990-2026 from utsports.com.

Runs on a machine with open internet (GitHub Actions). Tries several extraction
strategies against the official UT Athletics roster pages and falls back to the
Jina Reader text proxy. Writes data/rosters.full.json plus data/fetch-report.json,
and prints diagnostics for every season it cannot parse so the parser can be fixed.
"""
from pathlib import Path
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "rosters.full.json"
REPORT = ROOT / "data" / "fetch-report.json"
START_YEAR, END_YEAR = 1990, 2026
MIN_PLAYERS = 20

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

BAD_TOKENS = {
    "roster", "schedule", "news", "stats", "coaches", "staff", "football",
    "tennessee", "volunteers", "full bio", "bio", "name", "image", "position",
    "height", "weight", "hometown", "class", "view", "more", "twitter",
    "instagram", "facebook", "tickets", "shop", "watch", "listen",
}


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower().replace("’", "'")).strip()


def clean(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"^\[([^\]]+)\]\([^)]+\)$", r"\1", s.strip())
    s = s.replace("**", "")
    return re.sub(r"\s+", " ", s).strip(" \t\r\n-–—|")


def plausible(name):
    if not name or not (3 <= len(name) <= 60):
        return False
    if norm(name) in BAD_TOKENS:
        return False
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'’\-]+", name):
        return False
    if not re.search(r"[A-Za-z]{2}", name):
        return False
    return " " in name.strip()


def dedupe(names):
    out = {}
    for n in names:
        n = clean(n)
        if plausible(n):
            out.setdefault(norm(n), n)
    return list(out.values())


def get(url, timeout=45):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


# ---------------- extraction strategies ----------------

def s_next_data(doc):
    """Next.js / embedded JSON blobs with firstName+lastName fields."""
    names = []
    for m in re.finditer(r'<script[^>]*(?:id="__NEXT_DATA__"|type="application/json")[^>]*>(.*?)</script>',
                         doc, re.S):
        try:
            blob = json.loads(m.group(1))
        except Exception:
            continue

        def walk(node):
            if isinstance(node, dict):
                first = node.get("firstName") or node.get("first_name")
                last = node.get("lastName") or node.get("last_name")
                if isinstance(first, str) and isinstance(last, str) and first and last:
                    names.append(f"{first} {last}")
                full = node.get("fullName") or node.get("full_name") or node.get("name")
                if isinstance(full, str) and " " in full:
                    names.append(full)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(blob)
    return names


def s_sidearm(doc):
    """Classic Sidearm Sports roster markup."""
    names = []
    for m in re.finditer(r'sidearm-roster-player-name.*?</(?:div|li|td)>', doc, re.S):
        block = m.group(0)
        for a in re.finditer(r'<a[^>]*>(.*?)</a>', block, re.S):
            names.append(a.group(1))
        if not re.search(r'<a[^>]*>', block):
            for h in re.finditer(r'<h[1-6][^>]*>(.*?)</h[1-6]>', block, re.S):
                names.append(h.group(1))
    return names


def s_player_links(doc):
    """Anchors that point at an individual player's roster bio page."""
    names = []
    pat = re.compile(r'<a[^>]+href="[^"]*/(?:roster|player)[^"]*"[^>]*>(.*?)</a>', re.S | re.I)
    for m in pat.finditer(doc):
        txt = clean(m.group(1))
        if plausible(txt):
            names.append(txt)
    return names


def s_aria_bio(doc):
    """aria-label="Full Bio for Jane Doe" / title attributes."""
    names = []
    for m in re.finditer(r'(?:aria-label|title)="\s*(?:Full Bio(?: for)?|View Full Bio for)\s+([^"]+)"', doc, re.I):
        names.append(m.group(1))
    for m in re.finditer(r'Full Bio for\s+([^\n\r<|]+)', doc, re.I):
        names.append(m.group(1))
    return names


def s_table(doc_or_md):
    """Markdown table rows (Jina output) or HTML table rows: jersey | name | ..."""
    names = []
    for raw in doc_or_md.splitlines():
        line = raw.strip()
        if "|" not in line:
            continue
        cells = [clean(c) for c in line.split("|")]
        cells = [c for c in cells if c != ""]
        if len(cells) < 2:
            continue
        if re.fullmatch(r"\d{1,3}", cells[0]) and plausible(cells[1]):
            names.append(cells[1])
    return names


STRATEGIES = [
    ("next_data", s_next_data),
    ("sidearm", s_sidearm),
    ("aria_bio", s_aria_bio),
    ("player_links", s_player_links),
    ("table", s_table),
]


def extract(doc):
    """Return (names, strategy_name, per_strategy_counts)."""
    counts = {}
    best, best_name = [], "none"
    for name, fn in STRATEGIES:
        try:
            got = dedupe(fn(doc))
        except Exception as exc:
            counts[name] = f"error: {exc}"
            continue
        counts[name] = len(got)
        if len(got) > len(best):
            best, best_name = got, name
    return best, best_name, counts


def candidate_urls(year):
    base = "https://utsports.com/sports/football/roster"
    return [
        f"{base}/season/{year}",
        f"{base}/{year}",
        f"{base}?season={year}",
    ] + ([base] if year == END_YEAR else [])


def fetch_year(year, log):
    attempts = []
    for url in candidate_urls(year):
        try:
            doc = get(url)
        except urllib.error.HTTPError as e:
            attempts.append({"url": url, "error": f"HTTP {e.code}"})
            continue
        except Exception as e:
            attempts.append({"url": url, "error": str(e)[:120]})
            continue
        names, strat, counts = extract(doc)
        attempts.append({"url": url, "bytes": len(doc), "strategy": strat,
                         "found": len(names), "per_strategy": counts})
        if len(names) >= MIN_PLAYERS:
            return names, {"source": url, "strategy": strat, "attempts": attempts}
        # Keep a sample of the page so the parser can be corrected next run.
        if len(doc) > 400 and "sample" not in attempts[-1]:
            body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", doc, flags=re.S | re.I)
            body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
            attempts[-1]["sample"] = body[:600]
            attempts[-1]["markers"] = {
                k: doc.lower().count(k)
                for k in ["sidearm-roster-player", "__next_data__", "roster/player",
                          "full bio", "s-person", "person__name", "roster-card"]
            }

    # Fallback: Jina Reader text proxy.
    try:
        md = get("https://r.jina.ai/https://utsports.com/sports/football/roster/%d" % year, timeout=60)
        names = dedupe(s_table(md)) or dedupe(s_aria_bio(md))
        attempts.append({"url": "jina", "found": len(names)})
        if len(names) >= MIN_PLAYERS:
            return names, {"source": "jina", "strategy": "table", "attempts": attempts}
    except Exception as e:
        attempts.append({"url": "jina", "error": str(e)[:120]})

    return [], {"source": None, "strategy": None, "attempts": attempts}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seed_path = ROOT / "data" / "rosters.seed.json"
    rosters = json.loads(seed_path.read_text()) if seed_path.exists() else {}
    if OUT.exists():
        rosters.update({k: v for k, v in json.loads(OUT.read_text()).items() if len(v) >= MIN_PLAYERS})

    report = {}
    for year in range(START_YEAR, END_YEAR + 1):
        key = str(year)
        if len(rosters.get(key, [])) >= MIN_PLAYERS:
            print(f"{year}: have {len(rosters[key])} already", flush=True)
            report[key] = {"status": "cached", "count": len(rosters[key])}
            continue
        names, meta = fetch_year(year, print)
        if names:
            rosters[key] = sorted(names)
            print(f"{year}: OK {len(names)} via {meta['strategy']} <- {meta['source']}", flush=True)
            report[key] = {"status": "ok", "count": len(names), **meta}
        else:
            print(f"{year}: FAILED", flush=True)
            print(json.dumps(meta["attempts"], indent=2)[:2500], flush=True)
            report[key] = {"status": "failed", "count": 0, **meta}
        OUT.write_text(json.dumps(rosters, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        time.sleep(1.0)

    ok = sorted(int(y) for y, v in report.items() if v["status"] in ("ok", "cached"))
    bad = sorted(int(y) for y, v in report.items() if v["status"] == "failed")
    print(f"\n=== {len(ok)}/{END_YEAR-START_YEAR+1} seasons ===")
    print("got:", ok)
    print("missing:", bad)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
