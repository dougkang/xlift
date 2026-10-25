# Quickstart: Validating xLift and the Fragility Penalty

## Prerequisites

- Real database loaded from 2022-23 through the current season (dAB's history). The 006
  quickstart covers the load commands.
- `analysis/` synced (`cd analysis && uv sync`) for the parity checks.

## 1. Tests and gates

```bash
cd backend
uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run lint-imports
cd ../frontend && npm run gen:api && npm test
```

The `gen:api` step needs `ffm serve` running. Expected: all pass, including the new unit tests
(xLift, dAB) and integration tests (fragility options, rows, picker order, tactical opponent).

## 2. Parity with the analysis notebook (SC-001, SC-005)

```bash
cd analysis && uv run python xlift_parity.py
```

Expected:
- `max |xLift app − notebook| over free agents ≤ 0.05` — PASS (both under Last 15, research R10)
- `max |dAB app − availability report| over rostered players ≤ 0.001` — PASS

## 3. Last 15 equals today (SC-004)

The integration test runs the fixture analysis with `fragility="last15"` and compares it with
results recorded from the pre-feature code. Expected: identical.

## 4. Picker order (SC-003) and swap check (SC-007)

These are integration tests on the impact fixture:
- free agents' `xlift` is non-increasing across `offset` pages and with a `query`;
- adding the top free agent and dropping the team's weakest active player changes the team's
  expected weekly category wins by the listed `xlift`, within ±0.05.

## 5. Performance (SC-006)

Time a cold analysis and a cold picker listing on the real league with the cache cleared. Use
the 006 quickstart's timing snippet; for the picker, add a `list_players` call. Expected:
- cold analysis ≤ 1.38 s (1.5 × 0.92 s);
- picker < 1 s.

## 6. In the app

`ffm serve --reload`, then open a team:
- the *Fragility Penalty* dropdown shows **dAB × tag**;
- the roster shows an **xLift** column, with your weakest active player at `0.00`;
- the picker's free agents are ordered by xLift;
- switching to **Last 15** reproduces the pre-feature numbers;
- switching to **None** gives every non-IL player full availability;
- in tactical mode, the opponent's roster shows xLift for the opponent.
