# Data Model: xLift Leaderboard (009)

No schema change. Everything is computed from the existing projections, rosters and format.

## PlayerAnalysisSettings (tool)

`tools/player_analysis/settings.py`, frozen.

| Field | Type | Rule |
|---|---|---|
| league_id | int | must exist (404) |
| team_id | int | must be in the league (404) |
| window | int | 1–82, default 82 |
| as_of | date \| None | defaults to today |
| fragility | `none` \| `last15` \| `dab` \| `dab_tag` | default `dab_tag` |
| games_per_period | int | fixed at 3 (`core.sim.GAMES_PER_PERIOD`), as in Impact Analysis |
| mode | `"strategic"` | fixed (research R5) |
| remaining | None | fixed: no tactical window |

These are the attributes the core caches key on (research R5), so equal settings share cached
projections, dAB and spreads with Impact Analysis's strategic mode.

## LeaderboardQuery (tool)

| Field | Type | Rule |
|---|---|---|
| evaluate_for | `team` \| `league` | default `team` (FR-008) |
| pool | `free_agents` \| `all` | default `free_agents` (FR-016) |
| top | int \| None | 10–50, multiple of 5, default 25 (FR-017); `None` = no limit, for Python callers only. The API enforces 10–50. |
| min_games | int | 1–15, default 5 (FR-018) |

## Eligible player (derived)

From the league's player details plus rostered players (research R6):
- inactive free agents are skipped;
- under `team`, the selected team's players are skipped;
- under `free_agents`, rostered players are skipped;
- players without a projection are skipped;
- players with `games_found < min_games` are skipped.

## Category breakdown (core, DB-free)

`core/value/xlift.py: score_candidates_by_category(team_idx, T, out_line, candidate_lines, fmt,
spread) -> ndarray (candidates, categories)`

`B[i, c] = Σ_{u≠t} [Φ((k_c(T_t − out + ℓ_i) − k_uc)/s_c) − Φ((k_c(T_t) − k_uc)/s_c)]`

- Rows sum to `score_candidates` (within 1e-9).
- Ratio categories come from summed makes and attempts; direction comes from `fmt.rank_key`.

`core/value/scenario.py`:
- `score_pool_by_category(scenario, team_id, pool_projections, fmt, gpp, spread,
  roster_projections) -> {player: ndarray(categories) | None}`: for one team (`team`).
- `score_league_by_category(scenario, pool_projections, fmt, gpp, spread, roster_projections)
  -> {player: ndarray(categories) | None}`: for each team with its own out line, the owner
  masked, NaN-mean over teams (`league`, research R3).

## LeaderboardEntry (tool → API)

| Field | Type | Meaning |
|---|---|---|
| player_id | int | |
| name | str | |
| nba_team | str \| None | |
| owner_team_id | int \| None | None = free agent |
| owner_label | str | fantasy team name or "Free agent" |
| status | str | latest injury status, as in the picker |
| games_found / games_requested | int | the projection's games |
| footnote | str \| None | `* found of requested games` when found < requested |
| xlift | float | net: the sum of `by_category` |
| by_category | list[float] | in the response's `categories` order |

**Ordering**: `xlift` descending, then name, then id. The server returns the first `top`.

## Leaderboard (API response)

`settings` (echo, including `mode: "strategic"`), `evaluate_for`, `team_id`, `team_name`,
`categories` (key, label, higher_is_better), `total` (eligible count before `top`), `entries`,
`warnings` (`UNSUPPORTED_FORMAT` only; empty otherwise).

## Frontend state

- **Shared** (`ffm.impact.v3`, unchanged): league, team, window and fragility are read and set by
  both tools. Moves and mode belong to Impact Analysis only.
- **Player Analysis** (`ffm.player-analysis.v1`, new): `evaluateFor`, `pool`, `top` and `minGames`, with the
  defaults above. An invalid or missing stored value falls back to its default.
- **Route**: `#/` (Impact Analysis, also the default for an unknown hash) or `#/player-analysis`.
