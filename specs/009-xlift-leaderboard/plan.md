# Implementation Plan: xLift Leaderboard, the Start of Player Analysis

**Branch**: `009-xlift-leaderboard` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-xlift-leaderboard/spec.md`

## Summary

Add a second tool, **Player Analysis**, whose first view is the rankings notebook's xLift
leaderboard. It shows one row per player, ranked by net xLift, with a horizontal bar stacked by
category (negative categories left of zero) and a tick at the net.

- **Backend**:
  - Move xLift's scenario scoring, the Fragility Penalty and the process caches from
    `tools/impact_analysis` into core, leaving re-exports behind (research R1), so the new tool
    shares the code without importing another tool.
  - Add a per-category breakdown next to the existing net score (R2), and a League scope that
    averages each player over every team but their own, each team with its own out line (R3).
  - A new tool package, `tools/player_analysis`, does eligibility, filters, ordering and the top
    *n* (R6), behind one endpoint, `POST /api/player-analysis/leaderboard` (R7).
- **Frontend**:
  - A `Shell` with hash routing and a plain-text nav, owning the shared settings state (R8).
  - A Player Analysis page with the shared controls (no Reset) and the leaderboard's own
    controls.
  - An Observable Plot stacked-bar chart (R9).
- **Docs**: a style-guide amendment for the new chart, and the Tool 2 doc (R10).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/React 19 (frontend)

**Primary Dependencies**: NumPy (scoring), FastAPI/Pydantic (contract), SQLAlchemy (reads),
React + Vite, Observable Plot 0.6.17 (already a dependency). No new dependencies.

**Storage**: SQLite, with no schema change

**Testing**: pytest (unit DB-free, fixture integration, contract), import-linter (a new
independence contract), Vitest/Testing Library, and the notebook parity script
(`analysis/xlift_parity.py`, SC-003)

**Target Platform**: local web app (`ffm serve`)

**Project Type**: web application (backend + frontend)

**Performance Goals**: the leaderboard in < 3 s cold on the real league for either scope
(SC-005). League scope is about 1.4M normal-CDF evaluations, vectorized per team.

**Constraints**:
- *Your team* values equal the strategic picker's (SC-001);
- Impact Analysis's numbers are unchanged (SC-007);
- the frontend only draws: no ranking or arithmetic in TypeScript (FR-009);
- deterministic (seeded spreads).

**Scale/Scope**:
- 18 teams × 10 actives; about 330 free agents plus about 170 rostered candidates;
- 9 categories × 17 opponents;
- 10–50 rows shown.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | The breakdown recomputes FG% and FT% from summed makes and attempts per swap (the existing `team_keys`). Direction comes from `fmt.rank_key`, so fewer TO is a gain. Tie rules: equal keys give a 0.5 win probability, and equal xLift is ordered by name, then id. |
| II. Pluggable formats | ✅ | The breakdown and the response's `categories` come from `fmt.categories`, and the frontend colors by index. No category names in code. The palette's nine colors limit the chart to nine categories; a larger format needs a style amendment (spec Assumptions). |
| III. Simulation-driven | ✅ | xLift's weekly spreads come from the seeded per-period simulation (007). Same inputs give the same output. |
| IV. Tactical vs strategic | ⚠️ justified | Strategic only, declared in the settings and echoed (`mode: "strategic"`). League-wide comparison, with availability from the Fragility Penalty. Offering its **None** option inherits 007's justified deviation (Complexity Tracking). |
| V. Visualization | ✅ (amendment) | Qualitative palette for unrelated categories; `#111` tick with a white halo; style chrome for nav, controls and help. The stacked-bar leaderboard is added to `docs/style.md` in the same change. |
| VI. Data orthogonality | ✅ | Reads only through `core.data`; no adapter or schema change. |
| VII. Modular core | ✅ | Shared xLift, fragility and cache logic moves into core (R1). The new tool imports core only, enforced by a new import-linter independence contract. The API stays thin, and the frontend renders the API's numbers. |
| Workflow gates | ✅ | Core unit tests (breakdown sums, League masking and averaging, direction, ratios); fixture integration tests (ordering, filters, scopes, picker parity, unchanged IA); frontend tests; notebook parity; docs updated in the same change. |

**Post-design re-check**: passing. The Principle IV item is justified below.

## Project Structure

### Documentation (this feature)

```text
specs/009-xlift-leaderboard/
├── plan.md
├── research.md          # R1–R10
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md           # POST /api/player-analysis/leaderboard
│   └── ui.md            # nav, page, chart, help
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── .importlinter                         # + independence: impact_analysis ⟂ player_analysis
└── src/ffmodel/
    ├── core/value/xlift.py               # + score_candidates_by_category
    ├── core/value/scenario.py            # MOVED from tools/impact_analysis/value.py (DB-free parts)
    │                                     #   + score_pool_by_category, score_league_by_category
    ├── core/value/__init__.py            # export the new functions
    ├── core/model/fragility.py           # MOVED from tools/impact_analysis/fragility.py
    ├── core/cache.py                     # MOVED: projections, dAB, spreads caches; league_spread
    ├── tools/impact_analysis/value.py    # re-exports core.value.scenario
    ├── tools/impact_analysis/fragility.py# re-exports core.model.fragility
    ├── tools/impact_analysis/cache.py    # keeps `original`; re-exports core caches; clear() both
    ├── tools/player_analysis/__init__.py # NEW package
    ├── tools/player_analysis/settings.py # NEW: PlayerAnalysisSettings, LeaderboardQuery
    ├── tools/player_analysis/leaderboard.py  # NEW: pool, scoring, filters, order, top n
    ├── api/schemas.py                    # + LeaderboardRequest, Leaderboard, LeaderboardEntry
    └── api/routes.py                     # + POST /api/player-analysis/leaderboard

backend/tests/
├── unit/test_xlift_by_category.py        # NEW: sums = score_candidates; direction; ratios
├── unit/test_league_scope.py             # NEW: owner masked; mean over teams; own out lines
└── integration/test_leaderboard.py       # NEW: order, filters, scopes, picker parity, IA unchanged

frontend/src/
├── main.tsx                              # render Shell
├── Shell.tsx                             # NEW: useScenario, useRoute, nav, current tool
├── state/route.ts                        # NEW: hash route hook
├── state/playerAnalysis.ts               # NEW: evaluateFor, pool, top, minGames (ffm.player-analysis.v1)
├── App.tsx                               # takes state/dispatch as props; keeps exports
├── components/Nav.tsx                    # NEW: plain-text tool nav
├── components/Controls.tsx               # optional Reset (hidden in Player Analysis)
├── player-analysis/PlayerAnalysis.tsx    # NEW: page, controls, scope line, moves note
├── player-analysis/Leaderboard.tsx       # NEW: Plot stacked bars, tick, legend, empty state
├── api/client.ts                         # + leaderboard()
├── api/schema.d.ts                       # regenerated
└── help/content.ts                       # + leaderboard, playerAnalysisSettings

frontend/tests/
├── shell.test.tsx                        # NEW: routes, nav, shared settings, mode kept
└── leaderboard.test.tsx                  # NEW: order, negative segment, empty, moves note

analysis/xlift_parity.py                  # + 009 Your team and League checks (R4)

docs/
├── style.md                              # amendment: stacked-bar leaderboard, tick halo, nav
├── tool2-player-comparison.md            # Tool 2: Player Analysis — the leaderboard (R10)
└── overview.md                           # Tool 2 entry → [Player Analysis](tool2-player-comparison.md)
```

**Structure Decision**: the existing web-app layout. The new tool is a sibling package of
`impact_analysis`; shared logic moves into core (research R1).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle IV ("strategic MUST account for availability"): the Fragility Penalty's **None** option | Player Analysis offers the same Fragility Penalty as Impact Analysis (FR-003), so values match across tools. Same justification as 007: None is an explicit user choice, the default is **dAB × tag**, and IL-slot players still get 0. | Leaving None out would make Player Analysis's settings differ from Impact Analysis's, so settings couldn't carry over (FR-004) and values wouldn't match for that option. |

## Notes

- `setup-plan.sh` couldn't run (the shell was unavailable when this plan was written), so this
  file was written by hand from the plan template. The feature directory is the one in
  `.specify/feature.json`.
- **Name**: the tool is **Player Analysis** (the user's choice, R10).
