# Research: Focus on an H2H Opponent

## R1. Where the focused view comes from

**Decision**: a new analysis setting, `focus_opponent_id` (strategic only). The backend renders the
focused view: the page sends the clicked opponent with its next analyze request, like any other
setting.

**Rationale**: two of the three focused pieces need numbers the page doesn't have, and the
constitution keeps statistics out of the frontend.
- The opponent's averages are already in every response (radar series).
- The chance of beating the opponent per category is P(win) + ½·P(tie), from the H2H row's odds;
  computing it in the page would be scoring logic in TypeScript.
- The opponent's **distribution** isn't sent at all; only the selected team's, the Leader's and the
  League Average's density curves are.

**Alternatives considered**:
- *Precompute every opponent's focused view in each response*: measured on the real league, the
  9 density curves cost ~20 ms per set; 17 opponents is ~0.35 s extra on every strategic request
  (now ~0.53 s), and ~17 × 9 × 4 × 96 extra numbers (about 1 MB of JSON). Rejected.
- *A separate focus endpoint*: duplicates the analysis's inputs (settings, moves) and the
  before/after logic. Rejected for one setting on the existing endpoint.

## R2. Keeping a focus click fast

**Decision**: cache each scenario's simulation internals (`Computed`), keyed by everything that
affects the simulation (the original-result cache's key, without the focus) plus the moves. Focus
only changes rendering, so a focus click hits this cache and skips simulation.

**Rationale**: profiling a warm strategic analysis on the real league (0.53 s): `_compute` is
0.47 s (team simulation 0.25 s, league win rates 0.21 s); rendering, including the density
curves, is ~0.06 s. With the cache a focus click costs the render, well inside SC-003. The cache
is a small LRU (8 entries) next to the existing original-result cache; with moves, the original
and the moved scenario are both cached, so a focus change re-renders both without simulating.

**Alternatives**: none needed; the original-result cache already sets the pattern (003 R1). Its
key gains the focus, since the original *result* is rendered with it; the `Computed` underneath
doesn't depend on it.

## R3. The focused response: same fields, focused values

**Decision**: under focus the response keeps its shape; the comparison fields hold the opponent's
values, and a top-level `focus` block names the opponent. This mirrors how Tactical mode reuses
`emphasis: "opponent"` and the `opponent` curve role.

| Field | Unfocused | Focused |
|---|---|---|
| `radar.series` | every team | the opponent (`emphasis: "opponent"`) and the selected team |
| `radar.series[].win_rate` | chance vs a random league team | chance in this matchup: yours P(win)+½P(tie), theirs 1 − yours |
| `radar.series[].ranks`, `normalized`, `area` | league | unchanged (league) |
| `radar.league` | League Average shape | `[]` |
| `category_table.rows[].league_average` | league average | the opponent's projected average |
| `category_table.rows[].win_rate` | chance vs a random league team | your chance vs the opponent |
| `curves[].series` | selected, leader/next best, league_average | selected, leader/next best, **opponent** (in place of league_average); the leader is dropped when it is the opponent |
| `league_shape`, `matchups`, `matchup_totals`, `header`, `rosters` | — | unchanged |

**Rationale**: the page's components already know how to draw an opponent; the before/after
builder compares like with like because the original is rendered with the same focus.

**Alternatives**: separate `focus_*` fields beside the league ones: doubles the table and radar
payload and makes the page choose between them; rejected.

## R4. Changes under focus

- Radar: as in Tactical, the opponent's original shape and tones are included when its active
  players changed (a trade with them).
- Per Category Ranking: the League column's change uses the *inverse* direction (a better opponent
  is worse for you), as Tactical's opponent average does; the Win % change is the change in your
  chance against them.
- Curves: the existing `means` changes for `selected` and `opponent` roles apply.

## R5. Validation

`focus_opponent_id` must be another team in the league: an unknown team is a 404 (as an unknown
team is today); the selected team itself is a 422. In Tactical it is ignored (normalized to null),
since H2H isn't shown there.

## R6. Page state

Focus lives in the scenario state (`focusOpponentId`), cleared by `setLeague`, `setTeam`,
`setMode`; kept by moves, undo, reset of moves, window, Fragility Penalty and radar scale; not
saved to session storage (spec: not kept across reloads). The H2H rows become focusable
(`tabIndex=0`, Enter/Space, `aria-pressed`), the focused row marked with the style guide's
selected treatment.

## R7. Measured (T026)

On the real league (18 teams, 25,000 iterations), warm: the unfocused analysis took 1.03 s on the
first call after a server reload, then each focus change (`focus_opponent_id` 2, 2, 5, then
cleared) took 0.05–0.06 s on the server. With the page's 250 ms request debounce, a click
updates in about 0.3 s (SC-003: ≤ 0.5 s).
