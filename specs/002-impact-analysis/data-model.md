# Data Model: Impact Analysis Tool

**There are no schema changes.** This feature only reads the 001 data contract, and its hypothetical
moves never reach the database (Constitution VII). Everything below exists in memory: frozen
Python dataclasses in `core`, plus Pydantic models at the API edge. The API shapes are in
[contracts/api.md](contracts/api.md).

## Core types

### ScoringFormat / Category (`core/scoring`)

The full interface is in [contracts/scoring-format.md](contracts/scoring-format.md).

| Type | Fields | Rules |
|---|---|---|
| `Category` | `key` (e.g. `fg_pct`), `label` (`FG%`), `kind` (`additive` \| `ratio`), `stat` (additive) or `numerator`/`denominator` (ratio), `higher_is_better: bool`, `decimals` | `kind=ratio` requires a numerator and denominator. Ratios display with 3 decimals as `.473` (style guide). |
| `ScoringFormat` | `id` (`9cat_h2h`), `name`, `categories: tuple[Category,…]`, `base_stats: tuple[str,…]` (drawn), `derived_stats: dict[str, Callable]` (e.g. PTS) | `base_stats` is every raw stat the categories need, minus the derived ones. |

### PlayerProjection (`core/model`)

| Field | Type | Rules |
|---|---|---|
| `player_id` | int | |
| `games_found`, `games_requested` | int | `games_found ≤ games_requested`; `is_short = found < requested` (FR-007) |
| `mean` | vector[len(base_stats)] | Per-game mean |
| `chol` | matrix | Cholesky factor of the shrunk covariance (research R1); `None` when `games_found = 0` |
| `mean_stderr` | vector | √diag(Σ/n). Kept for future fit-error propagation, not used yet |
| `availability` | float in [0, 1] or None | Strategic p (research R4) |
| `games_remaining` | int ≥ 0 | Tactical k for the chosen period (research R5) |

### Scenario (`core/scenario`)

The scenario is immutable. Each move returns a new `Scenario`.

| Field | Type | Rules |
|---|---|---|
| `league` | `LeagueSettings` (001) | Includes `active_roster_capacity` |
| `rosters` | map team_id → tuple of `(player_id, slot)` | `slot ∈ {active, reserve}` |
| `owner` | map player_id → team_id | Derived. A player not in the map is a free agent |

**Invariants**, checked after every transition:
- Each team's active count is at most `active_roster_capacity`.
- A player is on at most one team.
- A reserve slot holds only a player who held it in the base snapshot (FR-022).

**Transitions** (research R7). Each one returns a new scenario or raises `MoveError(code)`.

| Move | Preconditions | Effect |
|---|---|---|
| `Drop(player)` | `player` is on the selected team | Removed; becomes a free agent |
| `Add(player)` | `player` is a free agent; the selected team has an open active slot | Added in an active slot |
| `Swap(acquire, give)` with `give` on the selected team | `acquire` is on another team T | `give` → T in an active slot, in `acquire`'s place; `acquire` → selected team, active |
| `Swap(acquire, give)` with `give` a free agent | `acquire` is on another team T; the selected team has an open active slot | `give` → T, active; `acquire` → selected team, active |

**Error codes**: `NOT_ON_TEAM`, `NOT_FREE_AGENT`, `NO_ACTIVE_SLOT`, `SAME_TEAM`, `UNKNOWN_PLAYER`.
The base scenario is rebuilt from 001 `get_league` on every request, so **Reset** is just an empty
move list.

### AnalysisSettings (`tools/impact_analysis`)

| Field | Default | Rules |
|---|---|---|
| `league_id` | — | Must exist |
| `team_id` | — | The selected team; must be in the league |
| `mode` | `strategic` | `strategic` \| `tactical` |
| `window` | 15 | 1–82 (FR-002) |
| `as_of` | today | Analysis date (research R4) |
| `opponent_id` | None | Tactical only. Required to compute tactical results; must differ from `team_id` |
| `period_start`, `period_end` | The Mon–Sun week containing `as_of` | Tactical only. `period_start ≤ period_end` |
| `iterations` | 25,000 | 1,000–50,000 |
| `seed` | 20261023 | Any integer |
| `games_per_period` | 3 | Strategic only. Fixed in this feature; not shown in the UI |

### Simulation output (`core/sim`)

| Type | Fields |
|---|---|
| `TeamSamples` | `team_id`, `totals`: array[iterations, stats], team-level: clipped, rounded, made ≤ attempted, PTS derived |
| `CategorySamples` | `team_id`, `values`: array[iterations, categories]. Ratio values are NaN when attempts = 0 |
| `MatchupOdds` | `team_id`, `opponent_id`, `category`: per category `(p_win, p_tie, p_loss)`, `matchup`: `(p_win, p_tie, p_loss)` |

### AnalysisResult (`tools/impact_analysis` → API)

| Part | Contents | Spec |
|---|---|---|
| `header` | Team name, manager, mode, `record` {wins, losses, ties, unit: `matchups`\|`categories`}, `matchup_win_probability` (tactical) | FR-014 |
| `rosters` | Every team's roster under the scenario. Each player has: slot, status, NBA team, `games_found`/`games_requested`, `games_remaining` (tactical), and an `eligibility` block (research R7) | FR-018, FR-026 |
| `radar` | Categories (axes) and one series per team, each with `{team_id, ranks[], emphasis: selected\|opponent\|other}`. Tactical includes only the selected team and the opponent | FR-015 |
| `category_table` | Strategic: rank per category. Tactical: `{selected_avg, opponent_avg, diff, favors: selected\|opponent\|even}` | FR-016 |
| `curves` | For each category: `{x[], series:[{role: selected\|leader\|next_best\|league_average\|opponent, team_id?, density[]}]}` | FR-017 |
| `matchups` | Strategic: one `MatchupOdds` per opponent. Tactical: one | FR-014 |
| `footnotes` | `[{player_id, text: "* 3 of 15 games"}]` for every short-history player in any roster shown | FR-007 |
| `warnings` | `NO_GAMES_REMAINING`, `OPPONENT_REQUIRED`, `UNSUPPORTED_FORMAT` | Edge cases |
| `freshness` | `nba_data_loaded_at`, `roster_as_of` | FR-005 |
| `settings_echo` | The effective settings, including the defaulted `as_of`, period, seed and iterations | SC-002 |

## New core read functions (`core/data`, extending 001's read interface)

| Function | Returns | Why |
|---|---|---|
| `get_last_n_games_bulk(conn, player_ids, n, *, as_of)` | `dict[player_id, GameWindow]` | One windowed SQL query (`ROW_NUMBER() OVER (PARTITION BY player_id …)`, portable) instead of about 550 calls |
| `count_team_games_bulk(conn, player_ids, start, end, *, statuses)` | `dict[player_id, int]` | Tactical games remaining for every picker row |
| `get_player_details(conn, *, league_id=None, player_ids=None)` | `dict[player_id, (PlayerSummary, latest status)]` | The picker pool (active plus rostered players), and details for players a move brings in (added during US2) |
| `get_data_freshness(conn, league_id)` | `{nba_data_loaded_at, roster_as_of}` | FR-005; reads `load_run` and `player_status` |

All three are regular-season only (FR-012), as 001's reads are. They are contract tests against
the 001 fixture dataset.
