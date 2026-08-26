# HANDOFF TO CLAUDE — Name a Vol

## What the user wants

Build a polished Tennessee Volunteers football version of a “Name a Dude” style roster-trivia game.

Core prompt example:

> Who played for the 1998 Tennessee Volunteers?

The user types any Tennessee player. If the player was on that season’s roster, it counts.

## Requirements already established

1. Include every Tennessee football season from **1990 through the current 2026 season**.
2. The player input must act like a real search box immediately when typing.
3. Autocomplete must search the **master name list across all seasons**, not only the year being asked.
4. Autocomplete suggestions should display **names only**. Do not display the player's years because that gives away the answer.
5. Support mouse/touch and keyboard Up/Down + Enter.
6. Current modes: Endless and Daily.
7. Current game gives three guesses, tracks score/streak, and tolerates minor spelling mistakes.
8. Keep this a clean-room implementation; do not copy That Guy Rocked proprietary code.

## Exact state of the code

The game engine/UI/autocomplete are working in `src/app.js`, `assets/styles.css`, and `index.html`.

The app has all 37 seasons in its year picker. **Only six roster arrays are physically bundled right now** (1998, 2001, 2004, 2007, 2015, 2022). For every other year, `src/app.js` fetches:

`https://r.jina.ai/https://utsports.com/sports/football/roster/YEAR`

and parses the public UT Athletics roster table, then caches that roster in `localStorage`.

A handoff script is included at `scripts/fetch_all_rosters.py`. Run it with internet access to generate `data/rosters.full.json` for 1990–2026, then run `scripts/validate_rosters.py` and `scripts/build_single_file.py`.

## Recommended next work

- First, generate and validate a complete offline `data/rosters.full.json` covering all 37 seasons.
- Inspect duplicates / spelling variants / suffixes (`Jr.`, `III`, apostrophes, etc.).
- Make autocomplete selection submit immediately if that feels better than a second Submit click.
- Consider adding position/jersey metadata later, but **do not expose season/year in autocomplete**.
- Improve mobile polish and loading state.
- Consider a deterministic Daily puzzle keyed to Eastern Time and a share grid.
- Publish as a static GitHub Pages project.

## Branding / legal posture

Current name is **Name a Vol**. It is an independent fan project and should state that it is not affiliated with or endorsed by the University of Tennessee, NCAA, or SEC. Avoid copying That Guy Rocked source code or protected visual assets.

## Files to inspect first

1. `HANDOFF_TO_CLAUDE.md`
2. `README.md`
3. `src/app.js`
4. `data/rosters.seed.json`
5. `scripts/fetch_all_rosters.py`
6. `dist/name-a-vol-single.html`
