# Contract: Roster File Input Format

Reference instance: `~/dev/ccsv-rumble-page/data/rosters.csv` (184 rows, 18 teams). This file
is used for manual validation only; tests use a small synthetic file under `backend/tests/fixtures/`.

UTF-8 CSV with a header row and RFC 4180 quoting (positions are quoted when they contain a comma).

| Column | Required | Example | Mapping |
|---|---|---|---|
| `team_id` | yes | `t.01` | `fantasy_team.source_team_key` |
| `player_id` | yes | `nba.p.5473` | `player_external_id(source=--source, external_id)` |
| `name` | yes | `N. Alexander-Walker` | Used for matching only (research R7) |
| `positions` | no | `G,FC` | `roster_entry.source_positions`, stored as-is |
| `nba_team` | no | `ATL` | Tie-breaker for matching only; never overrides NBA data |
| `status` | no | blank, `Q`, `O`, `IL`, `IL+`, `NA`, `DTD`, `GTD`, `SUSP` | `player_status` (blank → `healthy`); `IL`/`IL+`/`NA` → `roster_entry.slot = reserve` |
| `team_name` | yes | `Keyboard Cats` | `fantasy_team.name`; must be the same on every row of a team |
| `manager` | yes | `Doug Kang` | `manager.display_name` (one manager per name per league) |

## Rejection rules

All violations are collected and reported together. Nothing is written when any rule fails.

1. A required column is missing, or a required value is empty.
2. `team_name` or `manager` differs between rows with the same `team_id`.
3. The same player, after matching, appears more than once (FR-017).
4. A team has more `active`-slot players than `--capacity` (FR-017).
5. A row has no confident match to an NBA player (FR-016).
6. A `status` value is not in the allowed set.
