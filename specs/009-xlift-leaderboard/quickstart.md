# Quickstart: Validating the xLift Leaderboard (009)

## Prerequisites

- The real database loaded (see the 006 and 007 quickstarts).
- `analysis/` synced (`cd analysis && uv sync`) for the parity checks.

## 1. Tests and gates

```bash
cd backend
uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run lint-imports
cd ../frontend && npm run gen:api && npm test
```

`gen:api` needs `ffm serve` running. Expected: all pass, including:
- the new import-linter contract (Impact Analysis and Player Analysis are independent);
- unit: the breakdown's row sums equal `score_candidates` (≤ 1e-9); League scope masks the owner
  and averages per category; direction (TO) and ratio recompute;
- integration (fixture):
  - ordering and ties by name;
  - `top` and `min_games`;
  - the pools, and the selected team's players under each scope;
  - `xlift` = the sum of `by_category` (SC-002);
  - leaderboard `team` = the strategic picker's `xlift` for every shared player (SC-001);
  - the picker's and the analysis's numbers unchanged (SC-007);
- frontend:
  - the navigation and routes, and shared settings carried across tools;
  - the chart's rows in server order, with a negative segment left of zero;
  - the empty state, and the moves note.

## 2. Parity with the notebook (SC-003)

```bash
cd analysis && uv run python xlift_parity.py
```

Expected, under Last 15 (research R4):
- `SC-001 (007)`: unchanged, PASS.
- `009 Your team: max |leaderboard − notebook| ≤ 0.05`: PASS.
- `009 League: max |leaderboard − notebook| ≤ 0.05`: PASS. If any team has an open active slot, the
  script names those teams and applies the bound to the comparison without them.

## 3. Performance (SC-005)

With the caches cleared, time the leaderboard call on the real league for both `evaluate_for`
values (the 006 quickstart's timing snippet, calling the tool's `leaderboard`). Expected: each is
under 3 s cold, and well under 1 s warm.

## 4. In the app

`ffm serve --reload`, then:
1. Impact Analysis shows the nav with **Impact Analysis** marked; nothing else changed.
2. Click **Player Analysis**:
   - the same league, team, window and Fragility Penalty are selected;
   - 25 free agents are shown, sorted by xLift, each with a colored, category-stacked bar and a
     black tick.
3. Hover a segment: player, category, value. Compare a player's net with the Impact Analysis
   picker: equal.
4. Find a player with a negative FG% or FT% segment: it extends left of zero, and the tick sits at
   the net.
5. Switch to **League**: the values change; switching teams no longer changes them.
6. **All players**: rostered players appear, labeled with their team.
7. **Show top** 50, **Min games** 15: the list changes accordingly. If no player qualifies, the
   chart is replaced by "No players match these filters."
8. Make a move in Impact Analysis, then come back: the moves note shows, and the leaderboard is
   unchanged.
9. Go back to Impact Analysis: the move and the mode (e.g. tactical) are as you left them.
