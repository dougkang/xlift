# Implementation Plan: Current Matchup (Tactical Week-to-Date Actuals)

**Branch**: `005-tactical-actuals` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-tactical-actuals/spec.md`

## Summary

Tactical mode becomes the current matchup.

- **Import:** a new adapter imports the exporter's `matchups.csv`. It holds week-to-date team
  totals and pairings, and its as-of date and period are inferred from the file's modified date.
  The import writes a one-per-league matchup state through migration 0002.
- **Engine:** core adds each team's totals to its simulated remaining games after clipping.
  Remaining games are those after the as-of date and through the period end.
- **API:** reports the opponent, the current score, the week-to-date values and new warnings.
- **Frontend:**
  - removes the vs and Week controls;
  - shows a "Now" score line;
  - replaces H2H with the opponent's read-only roster;
  - updates the help.
- **Strategic:** unchanged.

## Technical Context

**Language/Version**: Python ≥3.12 (venv 3.14); TypeScript 5.9 / React 19

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy Core, NumPy, Typer; React, Vite,
Observable Plot and D3 (none new)

**Storage**: SQLite through plain-SQL migrations (adds `0002_matchup_state.sql`)

**Testing**: pytest (unit and integration on the `impact_dataset` fixture, plus a real-file
import test marked `live`); Vitest + React Testing Library with regenerated fixtures

**Target Platform**: Local `ffm serve` (:8000) and a desktop or mobile browser

**Project Type**: Web app (`backend/` + `frontend/`)

**Performance Goals**: The import takes under 5 seconds. Tactical analysis latency is unchanged
(it's the same simulation plus a vector add).

**Constraints**:
- Constitution VI: the adapter doesn't import core.
- Constitution I: no clipping bias; ratios from makes and attempts.
- No layout shift.
- The 004 help stays at 120 words or fewer.

**Scale/Scope**: 1 league, 18 teams, 9 pairings. About 4 backend modules touched plus 1 new
adapter, and about 6 frontend components.

## Constitution Check

*GATE: checked before Phase 0 research and again after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | The base is added after clipping (research R3). FG% and FT% come from combined makes ÷ attempts. The current score uses `fmt.compare`, with ties explicit. |
| II. Pluggable formats | ✅ | Core maps the fixed stat vocabulary to `fmt.base_stats` and reports missing stats. The adapter is format-agnostic. |
| III. Simulation-driven | ✅ | The remaining games are still Monte Carlo simulated. The base is a deterministic offset, and seeds are unchanged. |
| IV. Tactical vs strategic | ✅ | The mode changes the computation (base plus remaining by date). The logic lives in core and settings normalization. |
| V. Visualization | ✅ | The "Now" values are muted and differences stay first. The opponent's roster reuses the Roster style. No new colors. |
| VI. Data source orthogonality | ✅ | A new adapter writes only to the schema. The schema change goes through migration 0002. Dates are inferred inside the adapter. |
| VII. Modular core | ✅ | `get_matchup_state` is in `core.data`, and the base and current-score helpers are in core. The tool consumes them, and the API stays thin. |
| Domain constraints | ✅ | Hypothetical moves stay in memory, and the base is never written back. |

**Post-design re-check**: still passing. Fixing the stat vocabulary in the schema is a contract
change made through a migration, as Principle VI requires.

## Project Structure

```text
specs/005-tactical-actuals/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/{matchups-csv.md, api.md, ui.md}
└── tasks.md                      # /speckit-tasks

backend/src/ffmodel/
├── contract/migrations/0002_matchup_state.sql
├── adapters/matchup_csv/{__init__,parse,loader}.py       # new; + file-mtime as-of
├── adapters/roster_csv/loader.py                         # as_of default → file mtime
├── adapters/common.py                                    # file_date(path) helper
├── core/data/{matchup.py, models.py, __init__.py}        # MatchupState, get_matchup_state
├── core/sim/engine.py                                    # simulate_team(base=...)
├── core/model/projection.py                              # remaining window (as_of+1, end], by date
├── core/data/bulk.py                                     # count_team_games_bulk: exclude postponed/cancelled
├── tools/impact_analysis/{settings,analysis,cache}.py    # derive opponent/period; base; current score; warnings
├── api/{schemas,routes}.py                               # LeagueDetail.current_matchup; result fields
└── cli.py                                                # `ffm load matchups`
backend/tests/
├── unit/test_matchup_parse.py · unit/test_engine_base.py
├── integration/test_matchup_load.py · integration/test_impact_tactical.py (rewritten)
└── fixtures/impact_dataset.py (+ matchup state) · export_frontend_fixtures.py

frontend/src/
├── state/scenario.ts             # drop opponent/period
├── components/Controls.tsx       # remove vs/Week; disable Tactical without matchup
├── components/RecordHeadline.tsx # Now / Final line, period
├── components/CategoryTable.tsx  # Now column
├── components/Roster.tsx         # title prop; read-only reuse
├── App.tsx                       # opponent roster in place of H2H (tactical)
└── help/content.ts               # settings/mode/headline/categoryTable + opponentRoster
frontend/tests/ (tactical, help, help-content, changes, layout updated)
docs/style.md                     # Now line, opponent roster
```

**Structure Decision**: follow the existing layering. There is one new adapter package, one new
core data module, and the tactical branch of `analysis.py` is reworked. Strategic code isn't
touched apart from shared signatures, whose defaults keep today's behavior.

## Complexity Tracking

No violations.
