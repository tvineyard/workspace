# Name a Vol — Tennessee Football Roster Trivia

A clean-room fan game inspired by the general “name a player from a given team/year” trivia mechanic. It does **not** contain copied source code from That Guy Rocked.

## Current game behavior

- Tennessee Volunteers football only
- Seasons **1990 through 2026** are eligible
- A round displays one season and asks the player to name anyone on that roster
- Three guesses per round
- Endless and Daily modes
- Streak and score persist in `localStorage`
- Typing in the player box starts autocomplete across the **combined all-season player index**
- Suggestions show player names only, never seasons, so autocomplete does not reveal the answer
- Keyboard navigation: Up/Down + Enter; click/touch works
- Minor typo tolerance on submitted guesses

## Important roster-data status

The game recognizes 37 seasons, but the version handed off here physically bundles **six seed rosters**: 1998, 2001, 2004, 2007, 2015, and 2022. The app fetches the other official UT rosters at runtime through Jina Reader, parses the public UT Athletics roster page, and caches each result in browser `localStorage`.

To make the project completely self-contained, run:

```bash
python scripts/fetch_all_rosters.py
python scripts/validate_rosters.py
python scripts/build_single_file.py
```

That creates `data/rosters.full.json` and rebuilds the standalone HTML with all available roster data embedded.

## Run locally

Because the structured version uses external JS/CSS files, use any tiny local web server:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000/`.

For a zero-setup demo, open `dist/name-a-vol-single.html` directly.

## GitHub Pages

This project is static. Put the folder contents in the root of a public GitHub repo and enable Pages from the `main` branch/root. No build system is required.

## Data sources

See `data/season-sources.json`. The canonical roster pages are public University of Tennessee Athletics pages at `utsports.com`.

## Project structure

- `index.html` — structured app shell
- `assets/styles.css` — UI
- `src/app.js` — game engine, autocomplete, roster fetching/parsing, scoring
- `data/rosters.seed.json` — six physically bundled rosters
- `data/season-sources.json` — official URL for every year 1990–2026
- `data/roster-status.json` — exact bundled/missing status at handoff
- `scripts/fetch_all_rosters.py` — creates full offline roster JSON
- `scripts/validate_rosters.py` — verifies all 37 years exist
- `scripts/build_single_file.py` — embeds data/CSS/JS into one HTML file
- `dist/name-a-vol-single.html` — current standalone prototype
- `HANDOFF_TO_CLAUDE.md` — project context and requested next work
