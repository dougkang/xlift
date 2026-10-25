# Implementation Plan: League Shape Charts in the Category Breakdown

**Branch**: `008-league-shape-charts` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-league-shape-charts/spec.md`

## Summary

Add the rankings report's two league-shape views to each category of the strategic Category
Breakdown:

- **League shape**: every team's projected value against its place (1 = best).
- **Against null**: the gap to reach each place (bars), against the gap a normal league of the
  same size and spread would show (a line).

The selected team is marked in both charts.

A DB-free core function turns the analysis's per-team projected averages into, per category:
- places (ordered by the existing competition ranks, ties broken by team);
- values;
- gaps between consecutive places;
- null gaps (Blom's expected normal order statistics × the values' SD).

The tool adds team names, the selected team's climb and cushion marks, and, with moves, the
selected team's pre-move place and value (from the original analysis it already reuses). The API
gains one nullable field, `league_shape`, which is null in tactical mode. The frontend draws two
small charts under each category's distribution, in the style guide's palettes, with a
style-guide amendment for the two new chart idioms.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/React (frontend)

**Primary Dependencies**: NumPy (core), `statistics.NormalDist` (Blom quantiles, stdlib),
FastAPI/Pydantic (contract), React + `d3-scale` (already used by the radar) for the two new
charts

**Storage**: none (computed from the analysis's simulation results; no schema change)

**Testing**: pytest (DB-free unit tests for the core function, including a parity check with the
rankings report's formula; fixture integration tests for the result field), Vitest/Testing
Library (charts render, marks, strategic only)

**Target Platform**: local web app (`ffm serve`)

**Project Type**: web application (backend + frontend)

**Performance Goals**: adds ≤ 5% to an analysis's response time (SC-005); the computation is
9 categories × 18 teams, microseconds

**Constraints**: the frontend only draws (no ranking or gap arithmetic in TypeScript, FR-011);
deterministic; Constitution V palettes and an amendment to `docs/style.md` for the new chart
idioms

**Scale/Scope**: 18 teams, 9 categories, 17 gaps each

## Constitution Check

*GATE: must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | Values are the analysis's projected averages; FG% and FT% are already ratios of team totals. Places use the existing competition ranks (direction via `fmt.rank_key`), with an explicit tie rule (team id). Missing values are excluded, not zero-filled. |
| II. Pluggable formats | ✅ | The core function iterates `fmt.categories`; no category names. Direction and decimals come from the format. |
| III. Simulation-driven | ✅ | Values come from the simulation's projected averages, the same ones the ranking table shows. The null line is a closed-form reference, not a result. |
| IV. Tactical vs strategic | ✅ | Strategic only: it's a league-wide comparison (spec FR-015). Tactical is unchanged and gets `league_shape: null`. |
| V. Visualization | ✅ (amendment) | The selected team is emphasized in primary `#1C324A`; other teams muted in secondary shades; the null reference is tertiary `#898240` dotted, like the League Average line; the before marker is `#aaa` hollow, like the "before" distribution. Two new idioms (rank ladder, gap bars against a null line) are added to `docs/style.md` in the same change. |
| VI. Data source orthogonality | ✅ | No reads; nothing source-specific. |
| VII. Modular core | ✅ | `core/sim/shape.py` is DB-free. The tool assembles names and marks; the API is thin; the frontend renders the API's numbers. |
| Workflow gates | ✅ | Core unit tests (places, ties, direction, missing values, gaps, null gaps, parity with the report's formula), integration tests (field present in strategic, null in tactical, marks, before marker with moves), frontend tests, docs and help updated. |

**Post-design re-check**: passing. No violations, so no Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/008-league-shape-charts/
├── plan.md
├── research.md          # R1–R7
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md           # AnalysisResult.league_shape
│   └── ui.md            # two charts per category, marks, help
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/src/ffmodel/
├── core/sim/shape.py                 # NEW, DB-free: places, gaps, null gaps per category
├── core/sim/__init__.py              # export league_shape
├── tools/impact_analysis/analysis.py # strategic: league_shape with names, marks, before
└── api/schemas.py                    # LeagueShape models; AnalysisResult.league_shape

backend/tests/
├── unit/test_league_shape.py         # NEW
└── integration/test_impact_shape.py  # NEW

frontend/src/
├── components/LeagueShape.tsx        # NEW: League shape + Against null small charts
├── components/CategoryCurves.tsx     # render them under each category (strategic)
├── help/content.ts                   # breakdown help: the two charts, climb and cushion
└── api/schema.d.ts                   # regenerated

frontend/tests/
├── league-shape.test.tsx             # NEW
└── fixtures/strategic*.json          # league_shape added

docs/
├── style.md                          # amendment: rank ladder and gap-vs-null idioms
└── tool1-impact-analysis.md          # the breakdown's two charts
```

**Structure Decision**: the existing web-app layout. The core function sits with the other
display-series code (`core/sim/curves.py`); orchestration stays in the tool.
