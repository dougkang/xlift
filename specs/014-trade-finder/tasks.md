# Tasks: Trade Finder

## Phase 1: Setup
- [ ] T001 Baseline suites pass

## Phase 2: Foundational (core maths)
- [ ] T002 `trade_gains(ai, bi, T, lines_a, lines_b, fmt, spread)` in `backend/src/ffmodel/core/value/xlift.py`: (n_a, n_b) gains for A and B and A's per-category gains, both rosters changed (research R1)
- [ ] T003 [P] Unit tests in `backend/tests/unit/test_trade_gains.py`: gains equal a direct recompute of W for both teams; swapping identical lines gives 0; TO direction; per-category sums to A's gain
- [ ] T004 Scenario wrapper `trade_grid(scenario, a_team, b_team, projections, fmt, games_per_period, spread)` in `backend/src/ffmodel/core/value/scenario.py` (active, projected players only), exported from `core/value/__init__.py`

## Phase 3: US1 Win-win trades (P1)
- [ ] T005 [US1] `find_trades(conn, settings)` in `backend/src/ffmodel/tools/player_analysis/trades.py`: projections with the Fragility Penalty, league spread, per other team the balanced win-win pick (R3), per-category reasons (R4), FR-007 order, unsupported-format warning, NotFound for unknown league/team
- [ ] T006 [US1] `TradesRequest`, `Trade`, `TradeRow`, `TradesResult` in `backend/src/ffmodel/api/schemas.py`; `POST /api/player-analysis/trades` in `backend/src/ffmodel/api/routes.py`
- [ ] T007 [US1] Integration tests in `backend/tests/integration/test_trades.py`: one row per other team; both gains > 0 (SC-001); optimality by brute force over the grid (SC-002); gain equals a recompute from changed rosters (SC-003); order; reasons ≥ 0.1; API 404s
- [ ] T008 [US1] Frontend: regenerate `schema.d.ts`; `trades()` in `frontend/src/api/client.ts`; `Trades` table in `frontend/src/player-analysis/Trades.tsx`; section in `PlayerAnalysis.tsx` below the leaderboard, same shared settings
- [ ] T009 [US1] Styles in `frontend/src/styles/base.css`

## Phase 4: US2 Try it (P2)
- [ ] T010 [US2] Try it: `reset` + `addMove(swap)` on the shared state and navigate to `#/`; label notes replacing moves (`PlayerAnalysis.tsx`, `Trades.tsx`)
- [ ] T011 [US2] Frontend tests in `frontend/tests/trades.test.tsx`: rows, no-trade rows, reasons, Try it dispatches the swap and navigates

## Phase 5: Polish
- [ ] T012 Help topic `trades` in `frontend/src/help/content.ts` (≤ 120 words, no file names)
- [ ] T013 Docs: Trades in `docs/tool2-player-comparison.md`
- [ ] T014 Measure on the real league (SC-004); full suites, lint, build
