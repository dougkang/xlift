# Implementation Plan: xLift in Impact Analysis and the Fragility Penalty

**Branch**: `007-xwcwa-fragility-penalty` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-xwcwa-fragility-penalty/spec.md`

## Summary

Bring two models that exist only in `analysis/` into the app's core:

- **xLift**: a DB-free core module that scores players for a team. From each team's per-period
  totals and per-category weekly spreads, it computes expected weekly category wins against
  every other team (normal win odds). It finds the team's weakest active player and scores any
  per-period line as a swap for them, or, for a team's own players, against a copy of them.
- **dAB**: a DB-free availability model (counts by season age → blend) plus a core data read
  for multi-season games played and games available, with missed seasons inferred. The
  backtested parameters are fixed constants.

The tool layer:
- applies the selected **Fragility Penalty** (None / Last 15 / dAB / dAB × tag) to every
  projection's availability, before simulating;
- adds xLift to each roster row, scored for that row's team, which covers the opponent's roster
  in tactical mode;
- scores and sorts the whole picker pool for the selected team before paging.

The API gains a `fragility` setting and an `xlift` field on roster and picker rows. The frontend
gains a dropdown, a column in both tables, and help entries.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/React (frontend)

**Primary Dependencies**: NumPy (scoring, dAB), FastAPI/Pydantic (contract), SQLAlchemy (reads),
React/Vite (UI)

**Storage**: SQLite, with no schema change. dAB reads `player_game`, `game`, `player_team_stint`
and `player_status`, as today's reads do

**Testing**: pytest (unit DB-free, fixture integration, contract), Vitest/Testing Library, a
parity check against the `analysis/` notebook and modules (SC-001, SC-005)

**Target Platform**: local web app (`ffm serve`)

**Project Type**: web application (backend + frontend)

**Performance Goals**: cold analysis ≤ 1.5× today's (0.92 s, so ≤ 1.38 s); picker listing < 1 s
(SC-006)

**Constraints**: deterministic for the same inputs and seed (spreads use a fixed seed); core
DB-free where it computes (Constitution VII); frontend renders only (no scoring in TypeScript)

**Scale/Scope**: 18 teams × 10 actives; picker pool about 330 free agents plus about 170 other
rostered players; 9 categories × 17 opponents per score

## Constitution Check

*GATE: must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | Team totals sum makes and attempts; FG% and FT% come from team totals via `fmt.category_values`. Direction via `fmt.rank_key` (TO lower-is-better). Equal values give a 0.5 win probability, an explicit tie rule; picker ties are ordered by name. |
| II. Pluggable formats | ✅ | xLift iterates `fmt.categories` and `fmt.base_stats`; no category names in core or tools. dAB has no format dependence. |
| III. Simulation-driven | ✅ | Strategic results stay Monte Carlo. The weekly spreads for xLift come from a seeded per-period simulation, so they're reproducible. |
| IV. Tactical vs strategic | ⚠️ justified | Strategic "MUST account for availability". The **None** option removes the penalty by user choice (Complexity Tracking). The default (dAB × tag) and Last 15 / dAB all account for it. Tactical keeps its own games-remaining rule; xLift in tactical is explicitly the strategic-style measure (spec FR-011, FR-018). |
| V. Visualization | ✅ | One numeric column per table and one dropdown, in the existing style. No new colors or idioms. Values are signed with two decimals. |
| VI. Data source orthogonality | ✅ | dAB reads go through new `core.data` functions over the existing schema. No adapter or migration. |
| VII. Modular core | ✅ | `core/value/xlift.py` and `core/model/availability.py` are DB-free. `core/data/history.py` reads. The tool orchestrates; the API is thin; the frontend renders `xlift` from the API. |
| Workflow gates | ✅ | Core tests for xLift (direction, ratio recompute, ties, determinism), dAB (counts, missed seasons, blend, tags), fragility options, and a parity check with the notebook. Docs updated in the same change. |

**Post-design re-check**: passing. The Principle IV item is justified below.

## Project Structure

### Documentation (this feature)

```text
specs/007-xwcwa-fragility-penalty/
├── plan.md
├── research.md          # R1–R10
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md           # fragility setting; xlift on roster and picker rows; picker order
│   └── ui.md            # dropdown, columns, help
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/src/ffmodel/
├── core/value/__init__.py        # NEW package: player value measures
├── core/value/xlift.py           # NEW, DB-free: team keys, win odds, weakest player, xLift
├── core/model/availability.py    # NEW, DB-free: dAB counts → blend; constants; tag multipliers
├── core/data/history.py          # NEW reads: played/team-game dates, seasons, missed seasons
├── core/data/__init__.py         # export the new reads
├── core/sim/engine.py            # (unchanged) strategic_k uses proj.availability
├── tools/impact_analysis/settings.py   # fragility: Literal[...] = "dab_tag"
├── tools/impact_analysis/fragility.py  # NEW: apply an option to projections (+ dAB cache)
├── tools/impact_analysis/value.py      # NEW: per-period lines, spreads, xLift for a scenario
├── tools/impact_analysis/analysis.py   # apply fragility; xlift on roster rows; echo setting
├── tools/impact_analysis/picker.py     # score whole pool, sort, then page
├── tools/impact_analysis/cache.py      # cache dAB and spreads per settings key
├── api/routes.py                # pass fragility through; picker order
└── api/schemas.py               # ScenarioRequest.fragility; RosterPlayer/PlayerRow.xlift

backend/tests/
├── unit/test_xlift.py              # NEW
├── unit/test_availability_dab.py   # NEW
├── integration/test_fragility.py   # NEW: options, Last 15 = pre-feature, None, dAB × tag
├── integration/test_xlift_rows.py  # NEW: roster/picker xlift, order, paging, tactical opp
└── contract/test_offline_reads.py  # register history reads

frontend/src/
├── state/scenario.ts               # fragility setting (default "dab_tag")
├── components/Controls.tsx         # Fragility Penalty dropdown
├── components/Roster.tsx           # xLift column
├── components/PlayerPicker.tsx     # xLift column (order from server)
├── help/content.ts                 # help entries (no file names)
└── api/schema.d.ts                 # regenerated

analysis/
└── xlift_parity.py                 # NEW: SC-001 / SC-005 parity with the notebook and modules
```

**Structure Decision**: the existing web-app layout. New core packages are DB-free per
Constitution VII; orchestration lives in the tool.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle IV ("strategic MUST account for availability"): the **None** option removes the availability penalty | The user asked for a no-penalty view, to see per-game value without injury risk. It's an explicit, user-selected option. The default (**dAB × tag**) and the other two options account for availability, and None still zeroes players in IL slots. | Not offering None hides a view the user asked for. Reinterpreting None as Last 15 was rejected by the user, who asked for Last 15 to be its own option. |
