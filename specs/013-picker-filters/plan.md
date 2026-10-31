# Implementation Plan: Player Picker Filters and Category Sort

**Branch**: `013-picker-filters` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

## Summary

The Impact Analysis picker gains Position and Team filters and a Sort by categories choice. The
backend picker filters and ranks (research R1–R5), using the 009 per-category breakdown for the
sort; the frontend adds the controls (R6).

## Technical Context

**Language/Version**: Python 3.12+, TypeScript/React 19 · **Dependencies**: no new ones ·
**Storage**: SQLite, no schema change · **Testing**: pytest, Vitest · **Project Type**: web app ·
**Performance**: the category breakdown is computed only when a sort is picked (~same cost as the
leaderboard's) · **Constraints**: unchanged output with nothing picked (SC-004).

## Constitution Check

| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | Breakdown recomputes ratios from makes/attempts; TO direction via `rank_key`. |
| II. Pluggable formats | ✅ | Sort keys are the format's category keys, validated against it. |
| III. Simulation-driven | ✅ | Same seeded spreads as xLift. |
| IV. Tactical vs strategic | ✅ | xLift is the league-level weekly measure in both modes (007); unchanged. |
| V. Visualization | ✅ | Pills and a quiet multi-select in the style guide's control idiom; no new colors. |
| VI. Data orthogonality | ✅ | Reads through `core.data`. |
| VII. Modular core | ✅ | Breakdown from `core.value`; filters in the tool; page renders. |
| Workflow gates | ✅ | Integration tests per filter, the sort, parity with Player Analysis, unchanged default. |

## Project Structure

```text
backend/src/ffmodel/tools/impact_analysis/picker.py   # filters, category sort
backend/src/ffmodel/api/schemas.py, routes.py          # request fields, sort_xlift
backend/tests/integration/test_picker_filters.py
frontend/src/components/PlayerPicker.tsx               # controls, columns
frontend/src/help/content.ts, styles/base.css, api/schema.d.ts
frontend/tests/picker-filters.test.tsx
docs/tool1-impact-analysis.md
```

## Complexity Tracking

None.
