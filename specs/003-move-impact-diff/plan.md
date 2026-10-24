# Implementation Plan: Move Impact Highlighting

**Branch**: `003-move-impact-diff` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-move-impact-diff/spec.md`

## Summary

Show the impact of hypothetical moves everywhere the Impact Analysis page shows a projected value.

- **Server:** when a request has moves, it computes the **original**, the same settings with no
  moves. The original is cached and its untouched-team samples are reused. The server derives a
  `changes` block of signed, display-rounded deltas, each classified better / worse / neutral by a
  single tone table. It also returns result transitions, the original radar series, the original
  curves on a shared grid.
- **Page:** renders a shared `Delta` marker and the before/after visuals at the 9 places in the
  spec's inventory.

## Technical Context

**Language/Version**: Python ≥3.12 (venv 3.14); TypeScript 5.9 / Node 22

**Primary Dependencies**: unchanged from 002 (NumPy, FastAPI, Pydantic, React 19, D3, Observable
Plot)

**Storage**: SQLite. Read-only, no schema change.

**Testing**: pytest (unit, integration, `slow`); Vitest + RTL with a recorded fixture that has moves

**Target Platform**: local workstation, browser

**Project Type**: web application (existing `backend/` + `frontend/`)

**Performance Goals**: with moves, under 2 s per analysis (SC-001). The original is cached per
settings, and untouched teams are not re-simulated.

**Constraints**:
- changes and classifications are computed on the server only (FR-017);
- the deltas for untouched teams are exactly null (SC-003);
- `docs/style.md` is amended for the new colors (FR-018).

**Scale/Scope**:
- 9 page places;
- 1 new response block;
- 2 new curve roles;
- 1 cache.

## Constitution Check

*GATE: checked before Phase 0 research and again after Phase 1 design.*

| Principle | Status | How this plan complies |
|---|---|---|
| I. Statistically faithful aggregation | ✅ | Deltas are taken on values that are already faithful: ratio averages are still a ratio of means, and TO direction comes from the format's `higher_is_better`. |
| II. Pluggable scoring formats | ✅ | Tones come from `Category.higher_is_better`; no category names are hard-coded. |
| III. Distribution-based modeling | ✅ | The same seed and per-player streams mean the original and current results differ only by the moves. |
| IV. Tactical vs. strategic | ✅ | The `changes` block is mode-specific (W/L/T record vs. chance to win; ranking vs. difference table). |
| V. Visualization | ✅ (with amendment) | New `--better`, `--worse` and before/after tokens are added to `docs/style.md` (FR-018), as the principle requires. |
| VI. Data source orthogonality | ✅ | No data access changes. |
| VII. Modular core | ✅ | Diffing lives in `tools/impact_analysis/changes.py`. The core is untouched except for reusing existing types. Moves are still never written to the DB. |
| Tech stack | ✅ | The frontend renders server-classified changes only. |
| Quality gates | ✅ | Tests cover the tone table, inverted cases, zero suppression, transitions, sample reuse, and the cache. |

**Post-design re-check**: still passing. No Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/003-move-impact-diff/
├── plan.md
├── research.md      # R1 basis + cache + reuse · R2 precision · R3 tone table · R4 radar · R5 curves · R6 colors · R7 removed players not shown
├── data-model.md    # Change, Transition, changes block, cache
├── quickstart.md
├── contracts/
│   ├── api.md       # `changes` block
│   └── ui.md        # Delta marker + per-place rendering
└── tasks.md         # /speckit-tasks
```

### Source Code

```text
backend/src/ffmodel/
├── tools/impact_analysis/
│   ├── analysis.py      # refactor: `_compute()` internals vs `_render()`; original + reuse; curves with originals
│   ├── changes.py       # NEW: tone(), round_change(), transition(), build_changes(original, current)
│   └── cache.py         # + original-analysis LRU (8)
└── api/schemas.py       # + Change, Transition, Changes models; AnalysisResult.changes; new curve roles

backend/tests/
├── unit/test_changes.py                 # tone table, inverted cases, rounding, transitions
└── integration/test_impact_changes.py   # null without moves, untouched teams, trade/opponent, cache, all 9 places present

frontend/src/
├── components/Delta.tsx                 # NEW shared marker
├── components/{RecordHeadline,Radar,CategoryTable,CategoryCurves,RecordTable,App}.tsx  # render changes
├── styles/tokens.css, base.css          # + --better/--worse/--before-*, flip styles
└── format.ts                            # averages always 1 decimal (R2)
frontend/tests/changes.test.tsx          # each of the 9 inventory places + no-moves case (fixture with moves)

docs/style.md                            # "Change (before/after)" section (FR-018)
```

**Structure Decision**: extend the 002 web app in place. The diff logic gets its own module so the
analysis stays readable.

## Complexity Tracking

No violations.
