# Implementation Plan: Focus on an H2H Opponent

**Branch**: `011-h2h-opponent-focus` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-h2h-opponent-focus/spec.md`

## Summary

Clicking an opponent in the Strategic H2H table focuses the page on that matchup: the radar shows
two teams with matchup Win %, the Per Category Ranking's League and Win % columns show the
opponent's averages and your chance against them, and the Category Breakdown shows the opponent's
distribution in place of the league's.

- **Backend**: a `focus_opponent_id` setting (research R1). The analysis renders the focused
  fields in place (R3) and a `focus` block. A `Computed` cache keyed without the focus makes a
  focus click a re-render, not a re-simulation (R2). The change builder treats the opponent as
  Tactical does (R4).
- **Frontend**: focus in the scenario state (R6), sent with analyze requests; clickable,
  keyboard-reachable H2H rows; the League header names the opponent; the radar legend names
  them; help updated.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/React 19 (frontend)

**Primary Dependencies**: NumPy, FastAPI/Pydantic, React + Vite, Observable Plot, D3. No new
dependencies.

**Storage**: SQLite, no schema change

**Testing**: pytest (integration on the impact fixture, unit for the cache), Vitest/Testing Library

**Target Platform**: local web app (`ffm serve`)

**Project Type**: web application (backend + frontend)

**Performance Goals**: a focus click within 0.5 s on the real league (SC-003). Measured: a warm
strategic analysis is 0.53 s, of which simulation and league win rates are 0.47 s; with the
`Computed` cache, a focus change costs the ~0.06 s render.

**Constraints**: unfocused output unchanged (pre-010 regression); the frontend computes no
statistics; selected team's numbers identical with and without focus (SC-005).

**Scale/Scope**: 18 teams, 9 categories, 25,000 iterations.

## Constitution Check

| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | No aggregation change. Matchup Win % counts ties half, explicitly. Direction via `fmt.compare`; the opponent's average change uses the inverse direction. |
| II. Pluggable formats | ✅ | Categories come from the format; works under both standings rules. |
| III. Simulation-driven | ✅ | The opponent's distribution and odds are the same seeded simulation as the H2H row; the cache returns bit-identical `Computed` for identical inputs. |
| IV. Tactical vs strategic | ✅ | Focus is strategic only (ignored in tactical); computed in the tool, consumed by the page. |
| V. Visualization | ✅ | Reuses Tactical's opponent styling on the radar and curves; the focused row uses the existing selected-row treatment. No new colors. |
| VI. Data orthogonality | ✅ | No data or schema change. |
| VII. Modular core | ✅ | All focused numbers computed in the tool; the API stays thin (one request field); the page renders. |
| Workflow gates | ✅ | Integration tests for the focused fields, unchanged own-team numbers, cache hits; frontend tests for the interaction. |

**Post-design re-check**: passing.

## Project Structure

### Documentation (this feature)

```text
specs/011-h2h-opponent-focus/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
backend/src/ffmodel/
├── tools/impact_analysis/settings.py      # focus_opponent_id, normalized away in tactical
├── tools/impact_analysis/cache.py         # Computed cache; focus in the original key
├── tools/impact_analysis/analysis.py      # focused radar, table, curves; focus block
├── tools/impact_analysis/changes.py       # opponent tones/original, inverse league change
├── api/schemas.py, api/routes.py          # request field, Focus model, echo
backend/tests/integration/test_impact_focus.py
frontend/src/
├── state/scenario.ts                      # focusOpponentId
├── App.tsx, api/client.ts                 # send it; pass to components
├── components/RecordTable.tsx             # clickable rows (both layouts)
├── components/CategoryTable.tsx, Radar.tsx, CategoryCurves.tsx   # labels
├── help/content.ts
└── api/schema.d.ts
frontend/tests/focus.test.tsx
docs/tool1-impact-analysis.md
```

**Structure Decision**: existing layout; no new modules beyond the test files.

## Complexity Tracking

None.
