# Quickstart & Validation: Current Matchup

## A. Import

```bash
cd backend
uv run ffm db migrate
uv run ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv --league-key ccsv-2026
uv run ffm load matchups ~/dev/ccsv-rumble-page/data/matchups.csv --league-key ccsv-2026
```

**Expected:**
- the roster summary shows as-of = `rosters.csv`'s modified date;
- the matchup summary shows week 1, period 2026-10-19 → 2026-10-25, as-of =
  `matchups.csv`'s modified date, and 9 pairings (e.g. Keyboard Cats vs Triton Aggies).

Re-running the import replaces the state. A tampered file (e.g. `pts` changed) is rejected with
`BAD_TOTALS` and nothing is written.

## B. Automated

```bash
cd backend && uv run pytest && uv run ruff check . && uv run lint-imports
cd frontend && npm test && npm run build
```

| Check | Proves |
|---|---|
| Adapter: valid file loads; each validation label rejects; re-import replaces | US2, FR-001–FR-004, SC-004 |
| Engine: `base` is added after clipping; subset constraints hold; no base gives identical samples | FR-007, research R3 |
| Tactical: mean final = base + mean remaining, per category | SC-002 |
| Tactical with no games remaining: odds are 0, ½ or 1 and match `cat_wins` | SC-003, FR-011 |
| Opponent comes from the pairing for every team | SC-001, FR-006 |
| Moves change only remaining games; before and after share the base | FR-010, FR-019 |
| Strategic results are identical with and without a matchup state | SC-005 |
| Warnings: not loaded, stale, roster and matchup dates differ | FR-012, FR-017, FR-017a |
| Frontend: no vs or Week; Tactical disabled without a matchup; "Now" line; opponent roster has no drop buttons; help updated within 120 words | US3, FR-014–FR-018 |

## C. Browser

1. Run `ffm serve` and open the page in Tactical. Confirm the opponent is your real week-1
   opponent, the headline shows "Now" with the `cat_wins` score, and the as-of date is right.
2. Check the Per Category Difference "Now" values against the file. Ratios should be
   makes ÷ attempts.
3. Confirm the opponent's roster replaces H2H and has no − buttons.
4. Drop a player. Confirm only the projections move, and Now stays the same.
