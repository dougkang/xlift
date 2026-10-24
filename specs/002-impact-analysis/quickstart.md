# Quickstart & Validation: Impact Analysis Tool

This guide shows the feature works end to end. The shapes are in [contracts/api.md](contracts/api.md),
the layout in [contracts/ui.md](contracts/ui.md), and the model in [research.md](research.md).

## Prerequisites

- Feature 001 is loaded:

  ```bash
  cd backend
  uv run ffm load nba
  uv run ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv --league-key ccsv-2026 --season 2026-27 --capacity 10
  ```

- `uv` with `uv sync` already run in `backend/`.
- **Node 22 LTS** for the frontend (`node --version` ≥ 22). It isn't installed on the development
  machine as of 2026-10-23. Install it with `brew install node@22`, or with a version manager.

## A. Backend: offline checks (CI)

```bash
cd backend
uv run pytest            # unit + integration, network blocked
uv run lint-imports      # core ↛ tools/api, tools ↛ api, core ↔ adapters independent
```

| Check | Proves |
|---|---|
| Scoring conformance suite passes for `9cat_h2h` | Constitution II, contracts/scoring-format.md |
| FG% and FT% equal Σ makes / Σ attempts in every simulation; a zero-attempt ratio is a tie | SC-006, Constitution I |
| Synthetic league where team A leads every category → strategic record (N−1)–0–0, and rank 1 in all categories including TO | SC-005 |
| Streaming example: 2-game slightly-worse player beats 1-game better player in tactical mode; the order reverses in strategic | SC-004, Constitution IV |
| Same settings and seed twice → byte-identical `AnalysisResult` JSON | SC-002 |
| A move changes only the moved players' draws; unaffected teams' samples are identical before and after | research R2 (common random numbers) |
| Simulated counting-stat team means within 1% of Σ k·μ | research R2 (no clipping bias) |
| Every move rule and error code (`NO_ACTIVE_SLOT`, …); Reset = empty moves = base rosters; DB unchanged after analyze calls | FR-019–FR-024, SC-009 |
| API contract tests for each endpoint, warning and 422 shape | contracts/api.md |

## B. Backend: real-data checks (manual, against the 001 database)

```bash
cd backend
uv run pytest -m slow    # SC-001 timing and SC-003 seed stability on the real 18-team league
uv run ffm serve         # http://localhost:8000/api/health → {"status":"ok","schema_version":1}
```

Expected results:
- `/api/impact/analyze` for any team responds in under 2 s, in both modes (SC-001).
- Across 5 seeds, no matchup or category win probability moves by more than 3 points, for every
  team in both modes (SC-003).

## C. Frontend (needs Node)

```bash
cd frontend
npm install
npm run gen:api          # regenerate src/api/schema.d.ts from the running backend's /openapi.json
npm test                 # Vitest + Testing Library (mocked API)
npm run dev              # http://localhost:5173 (proxies /api → :8000)
```

Manual walk-through, with `ffm serve` running:
1. Choose CCSV Rumble and Keyboard Cats. The page shows the record headline, radar, ranks,
   9 curves with the leader and league average overlaid, and the roster. Any short-history player
   shows "* n of 15 games".
2. Press "−" on a player. The player appears in the picker as FA, and the record and ranks update
   within 2 s.
3. Press "+" on a free agent. It joins in an active slot. On a full roster, "+" is disabled and its
   tooltip says why.
4. Press "+" on another team's player. The swap dialog offers your roster, and also free agents if
   you have an open slot. Confirm, and both rosters update.
5. Switch to Tactical and choose an opponent. Games remaining appear in the roster and the picker.
   The record becomes categories, and the radar and curves show the opponent only.
6. Press Reset. The rosters match the loaded league. Reloading mid-session keeps your moves; a new
   tab starts fresh.
7. Check the style against `docs/style.md`:
   - Helvetica only;
   - no rounded corners or shadows;
   - yellow is used only for "yours" and "selected";
   - "−" is red.

## D. Build and serve together

```bash
cd frontend && npm run build
cd ../backend && uv run ffm serve      # serves frontend/dist at http://localhost:8000/
```

## Validation log

**2026-10-23**, real `ccsv-2026` league (18 teams), Python 3.14 (uv), Node 22.23, default 25,000
iterations:

- **A. Offline checks:** 237 backend tests and 16 frontend tests pass. Lint is clean, the
  6 import-linter contracts hold, and the frontend builds.
- **No database at import time:** `ffmodel.core.sim`, `ffmodel.core.scoring`,
  `ffmodel.core.model` and `ffmodel.core.scenario` import without loading SQLAlchemy. Getting
  there needed a split of `core/model` into a database-free `fit` module and a database-backed
  `projection` module; `contract/test_layering_002.py` now enforces it.
- **B. `pytest -m slow` on the real league** (95 s):
  - **SC-001:** a cold analysis takes 0.59 s and the slowest warm one 0.53 s, against a 2 s
    target.
  - **SC-003:** across 5 seeds, every team in both modes stays within **1.71 percentage points**
    on every matchup and category win probability, against a limit of 3.
- **C. API walk-through** (the same flow as the page):
  1. Strategic analysis in 0.61 s. Keyboard Cats project 1–16–0, with 9 curves and 2
     short-history footnotes ("* 1 of 15", "* 6 of 15").
  2. Dropping an active player re-analyzes in 0.52 s.
  3. The picker answers instantly. Free agents come first, with `can_add` true.
  4. Shai Gilgeous-Alexander (Elsie's World) offers `["roster", "free_agent"]`. Trading for him
     moves the record to 2–14–1.
  5. Tactical vs Elsie's World for Oct 19–25: categories 5–4–0, 66% to win. The radar shows
     2 series, and H2H stays league-wide with 17 rows.
  6. An empty move list (Reset) returns the base result exactly.
- **C. Browser:** the user reviewed the layout and style interactively throughout the session.
  Style changes are recorded in `docs/style.md` (subtle controls, red status text, radar fill,
  average lines and labels).
- **D. Single server:** `ffm serve` serves the built `frontend/dist` at `/` alongside `/api`.
