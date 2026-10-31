# Research: Trade Finder

## R1. The gain of a swap
**Decision**: for teams A and B swapping active players a and b, with weekly lines L (per-game mean
× availability × 3, as xLift), new totals T'_A = T_A − L_a + L_b and T'_B = T_B − L_b + L_a. A's gain
is W_A(T') − W_A(T), where W sums Φ((key_A − key_u)/s) over categories and every other team u, with
B's keys taken from T'_B (B is one of A's opponents). Same for B.
**Rationale**: FR-002. xLift's W with the league spread s; ratios recomputed from makes and
attempts; direction via `rank_key`.

## R2. Search
**Decision**: vectorized per team pair: an (n_A × n_B) grid of new totals for both teams, keys,
then W for each side against the fixed other teams plus the changed partner. ~10 × 10 swaps × 17
teams ≈ 1,700 swaps, each a 9 × 17 odds evaluation: milliseconds.
**Alternative**: simulate each swap: far too slow; xLift's analytic W is the shared measure anyway.

## R3. The balanced pick
**Decision**: among swaps with both gains > 0, maximize min(gain_A, gain_B); ties by larger sum,
then names (FR-003).

## R4. Category reasons
**Decision**: A's per-category gain = per-category W change (the 009 breakdown's form), reported
for categories with |Δ| ≥ 0.1, largest first (FR-005).

## R5. Where the code lives
**Decision**: the maths in `core/value/xlift.py` (`trade_gains`, DB-free) and a scenario wrapper
in `core/value/scenario.py`; the tool function `find_trades` in `tools/player_analysis/trades.py`;
`POST /api/player-analysis/trades`. Shares Player Analysis's projections, Fragility Penalty and
spread caches.

## R6. Try it
**Decision**: the page dispatches `reset` then `addMove({type: "swap", acquire_id: b, give_id: a,
team_id: A})` on the shared scenario state and navigates to Impact Analysis (`#/`). With moves
present, the button reads "Try it (replaces your moves)".

## R7. Measured (T014)
On the real league (18 teams), warm: 0.52–0.55 s per request (SC-004: < 3 s). 14 of 17 teams had a
win-win trade for the first team; the smallest shown gain was +0.08. A first version allowed any
positive gain and showed a trade at "0.00" (0.003 wins), so gains must now round to at least +0.01.
