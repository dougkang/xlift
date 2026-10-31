# Implementation Plan: Trade Finder

**Branch**: `014-trade-finder` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

## Summary
For the selected team and each other team, score every 1-for-1 active swap for both teams with
xLift's weekly expected-wins measure (both rosters changed), keep win-wins, show the most
balanced (research R1–R4). Core maths in `core/value`, a Player Analysis tool function and
endpoint (R5), a Trades section with Try it (R6).

## Technical Context
**Language**: Python 3.12+, TypeScript/React 19 · **Dependencies**: none new · **Storage**: SQLite,
no schema change · **Testing**: pytest (unit for the maths, fixture integration), Vitest ·
**Performance**: ~1,700 swaps per request, vectorized; < 3 s cold (SC-004).

## Constitution Check
| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | Ratios from summed makes/attempts; TO via `rank_key`; equal keys 0.5. |
| II. Pluggable formats | ✅ | Categories from the format; no names in code. |
| III. Simulation-driven | ✅ | Seeded weekly spreads shared with xLift. |
| IV. Tactical vs strategic | ✅ | Strategic only, league-wide comparison with availability (Fragility Penalty), declared in the echo. |
| V. Visualization | ✅ | A table in the style guide's idiom; signed green/red not used for gains (both positive by construction). |
| VI. Data orthogonality | ✅ | Reads through `core.data`. |
| VII. Modular core | ✅ | Maths in core; the tool imports core only; thin API; page draws. |
| Gates | ✅ | Unit tests (gain vs direct recompute, symmetry, direction), integration (win-win, optimality, order), frontend. |

## Project Structure
```text
backend/src/ffmodel/core/value/xlift.py, scenario.py, __init__.py   # trade_gains
backend/src/ffmodel/tools/player_analysis/trades.py                  # find_trades
backend/src/ffmodel/api/schemas.py, routes.py                        # endpoint
backend/tests/unit/test_trade_gains.py, tests/integration/test_trades.py
frontend/src/player-analysis/Trades.tsx, PlayerAnalysis.tsx, api/client.ts, help/content.ts, styles/base.css
frontend/tests/trades.test.tsx
docs/tool2-player-comparison.md
```

## Complexity Tracking
None.
