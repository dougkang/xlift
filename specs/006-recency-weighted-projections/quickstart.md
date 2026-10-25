# Quickstart: Validating Recency-Weighted Projections

## Prerequisites

- Backend and frontend installed (repo `README.md`).
- The real database loaded with **2022-23 through the current season**. The backtest needs
  three evaluated seasons plus one season of history:

  ```bash
  cd backend && uv run ffm load nba --season 2022-23 --season 2023-24 --season 2024-25
  uv run ffm load nba
  ```

- The analysis project synced: `cd analysis && uv sync`.

## 1. Tests and gates (FR-001–FR-012, SC-005)

```bash
cd backend
uv run pytest -q              # unit + fixture integration, including the new fit/shrinkage tests
uv run ruff check src tests
uv run lint-imports           # layering contracts still kept
cd ../frontend && npm test
```

Expected: all pass. The conformance suite confirms `unshrunk_stats` ⊆ `base_stats`.

## 2. Success criteria backtest (SC-001, SC-002, SC-003, SC-007)

```bash
cd analysis
uv run python projection_backtest.py
```

Expected output: one line per criterion, each with its measured value and PASS:

| Criterion | Threshold | Measured on the shipped code (2026-10-24, 6,001 player-cutoffs) |
|---|---|---|
| SC-001 counting stats, next 15, vs 15-game window | ≥ 20% lower error | +21.1% |
| SC-002 next 30 / next 60 | ≥ 20% each | +30.0% / +31.6% |
| SC-003 stars' (20+ pts) points bias, next 15 | within ±0.5 | +0.20 pts/game |
| SC-007 FG% / FT% vs unshrunk weighted fit, next 15 | ≥ 10% each | +10.7% / +20.1% |

The pre-implementation estimates (about 25% for SC-001) used a slightly different sample:
outcomes could run past the season's end. This script keeps outcomes within the season. SC-001
and FG% pass with small margins.

## 3. Availability unchanged (SC-004, FR-013)

Compare availability at window 15 and window 82 for every rostered player at the same as-of
date. They must be identical. A fixture integration test covers this; for the real league:

```bash
cd backend && uv run python -c "
from datetime import date
from ffmodel.contract.db import get_engine
from ffmodel.core.data import get_league
from ffmodel.core.model import build_projections
from ffmodel.core.scoring import get_format
eng = get_engine(); fmt = get_format('9cat_h2h'); d = date(2026, 10, 24)
with eng.connect() as c:
    ids = [r.player.player_id for t in get_league(c, 1).teams for r in t.roster]
    a = build_projections(c, ids, fmt, window=15, as_of=d, prior=None)
    b = build_projections(c, ids, fmt, window=82, as_of=d, prior=None)
print('identical availability:', all(a[p].availability == b[p].availability for p in ids))
"
```

## 4. Performance (SC-006)

Time a cold analysis of the real league before and after (cache cleared). The ratio must be ≤ 1.5:

```bash
cd backend && uv run python -c "
import time; from datetime import date
from ffmodel.contract.db import get_engine
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
with get_engine().connect() as c:
    cache.clear(); t = time.time(); analyze(c, AnalysisSettings(league_id=1, team_id=1, as_of=date(2026,10,24)))
    print(f'cold analyze {time.time()-t:.2f}s')
"
```

Measured on the same four-season database: 0.67 s before the change, 0.92 s after (1.37×).
The extra time is loading 82-game windows; the cache fetches the prior's pool once and reuses
it for the requested players.

## 5. In the app (US3, FR-015)

`uv run ffm serve`, then open the page:
- the *Last X games* input shows **82**;
- the settings help reads as in [contracts/ui.md](contracts/ui.md);
- players with fewer than 82 games show "* N of 82 games".
