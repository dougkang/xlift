# Data Model: League Data Schema (contract v1)

The DDL is in [contracts/schema.sql](contracts/schema.sql). This document explains each table, its
relationships, and its validation rules. Types are logical: in the DDL, DATE is ISO-8601 TEXT and BOOLEAN is INTEGER 0/1, for portability. All tables are source-neutral (FR-004). Anything specific
to a source lives only in `*_external_id` rows and in `load_run.source`.

```text
season ─┬─< game >── nba_team (home, away)
        │     └─< player_game >── player, nba_team (team played for)
        └─< fantasy_league ─< fantasy_team >── manager
                    └─< roster_entry >── player
player ─< player_external_id
player ─< player_team_stint >── nba_team
player ─< player_status
nba_team ─< nba_team_external_id
game ─< game_external_id
load_run (standalone audit log)
schema_migrations (managed by the migration runner)
```

## NBA side

### season

| Column | Type | Rules |
|---|---|---|
| season_id | TEXT PK | Format `YYYY-YY`, e.g. `2026-27`; CHECK length 7 |
| start_date | DATE | First regular-season game date |
| end_date | DATE | Last regular-season game date; `end_date >= start_date` |

### nba_team

| Column | Type | Rules |
|---|---|---|
| team_id | INTEGER PK | Internal ID |
| abbreviation | TEXT UNIQUE NOT NULL | e.g. `LAL` |
| city | TEXT NOT NULL | |
| name | TEXT NOT NULL | e.g. `Lakers` |

### player

| Column | Type | Rules |
|---|---|---|
| player_id | INTEGER PK | Internal ID, stable across loads |
| full_name | TEXT NOT NULL | Display name as the source gives it (`Luka Dončić`) |
| first_name, last_name | TEXT | |
| search_name | TEXT NOT NULL | `normalize_name(full_name)`; indexed (FR-023, research R7) |
| positions | TEXT | Comma-separated, normalized to `G`, `F`, `C` (e.g. `G,F`); FR-024 |
| current_team_id | INTEGER FK → nba_team NULL | NULL = unattached |
| is_active | BOOLEAN NOT NULL | On an NBA roster in the latest loaded season |

### player_external_id / nba_team_external_id / game_external_id

| Column | Type | Rules |
|---|---|---|
| source | TEXT | e.g. `nba_stats`, `yahoo`, `fixture` |
| external_id | TEXT | The source's ID, kept verbatim |
| *_id | INTEGER FK | The internal entity |
| match_method | TEXT | player table only: `exact` (the source gave the ID directly), `auto` (name-matched), `user` (confirmed by the user) |

PK `(source, external_id)`. For players: one internal player can have many external IDs, but one
(source, external ID) points to exactly one player. A `user` match is never overwritten by an
`auto` match.

### game

| Column | Type | Rules |
|---|---|---|
| game_id | INTEGER PK | Internal ID |
| season_id | TEXT FK → season NOT NULL | |
| season_type | TEXT NOT NULL | CHECK IN (`preseason`,`regular`,`all_star`,`playoffs`,`play_in`,`cup_final`); FR-012 |
| game_date | DATE NOT NULL | Local (US Eastern) game date |
| home_team_id, away_team_id | INTEGER FK → nba_team NOT NULL | CHECK they differ |
| status | TEXT NOT NULL | CHECK IN (`scheduled`,`final`,`postponed`,`cancelled`) |

Indexes: `(season_id, season_type, game_date)`, `(home_team_id, game_date)`,
`(away_team_id, game_date)`.

**Source mapping** (nba_stats): live games stay `scheduled` until final; see research R1.

**State transitions**: `scheduled → final`, `scheduled → postponed → scheduled` (new date) `→ final`,
`scheduled → cancelled`. A game's ID never changes when it is rescheduled; only `game_date`
changes, so a reschedule creates no duplicate.

### player_game (box score; one row per appearance)

| Column | Type | Rules |
|---|---|---|
| game_id | INTEGER FK → game | PK part |
| player_id | INTEGER FK → player | PK part |
| team_id | INTEGER FK → nba_team NOT NULL | Team played for in this game (US1 scenario 4); must be the game's home or away team |
| minutes | REAL NOT NULL | ≥ 0 (seconds-long appearances round to 0; research R1) |
| fgm, fga, fg3m, fg3a, ftm, fta | INTEGER NOT NULL | ≥ 0; `fgm ≤ fga`, `fg3m ≤ fg3a`, `ftm ≤ fta`, `fg3m ≤ fgm`, `fg3a ≤ fga` |
| oreb, dreb, reb | INTEGER NOT NULL | ≥ 0; `reb = oreb + dreb` |
| ast, stl, blk, tov, pf, pts | INTEGER NOT NULL | ≥ 0 |
| plus_minus | INTEGER | Nullable (not every source has it) |

- No percentages and no fantasy values are stored (FR-002, FR-003).
- A row exists only for a game the player appeared in, and only once the game is `final`.
  Absence means the player did not play (research R3).
- Index: `(player_id, game_id)`. "Last N" queries are ordered by game date through a join to
  `game`.

### player_team_stint

| Column | Type | Rules |
|---|---|---|
| player_id | INTEGER FK → player | PK part |
| team_id | INTEGER FK → nba_team | |
| start_date | DATE NOT NULL | PK part |
| end_date | DATE NULL | NULL = open (current team); `end_date >= start_date` |

Stints for one player do not overlap (the loader checks this, and a contract test enforces it).
Used for team games in a range, missed games (FR-021), and future games for tactical counts.

## Fantasy side

### fantasy_league

| Column | Type | Rules |
|---|---|---|
| league_id | INTEGER PK | |
| league_key | TEXT UNIQUE NOT NULL | User-chosen stable key (e.g. `ccsv-2026`); a reload targets the league by this key |
| name | TEXT NOT NULL | |
| season_id | TEXT FK → season NOT NULL | |
| scoring_format_id | TEXT NOT NULL | Identifier only, e.g. `9cat_h2h` (FR-003); default `9cat_h2h` |
| active_roster_capacity | INTEGER NOT NULL | > 0; default 10 (FR-017) |

### manager

| Column | Type | Rules |
|---|---|---|
| manager_id | INTEGER PK | |
| league_id | INTEGER FK → fantasy_league | |
| display_name | TEXT NOT NULL | UNIQUE `(league_id, display_name)`. The same name in one league is the same person (research R8) |

### fantasy_team

| Column | Type | Rules |
|---|---|---|
| fantasy_team_id | INTEGER PK | |
| league_id | INTEGER FK → fantasy_league | |
| source_team_key | TEXT NOT NULL | e.g. `t.01`; UNIQUE `(league_id, source_team_key)` |
| name | TEXT NOT NULL | |
| manager_id | INTEGER FK → manager NOT NULL | Not unique: one manager may run several teams |

### roster_entry

| Column | Type | Rules |
|---|---|---|
| league_id | INTEGER FK → fantasy_league | PK part |
| player_id | INTEGER FK → player | PK part: a player is on at most one team per league (FR-016) |
| fantasy_team_id | INTEGER FK → fantasy_team NOT NULL | Must belong to the same league |
| slot | TEXT NOT NULL | CHECK IN (`active`,`reserve`); `reserve` when the status is IL/IL+/NA (R8) |
| source_positions | TEXT | Verbatim from the file (`G,FC`); not used by tools |

- **Validation**: per team, `COUNT(slot = 'active') ≤ active_roster_capacity`. The loader checks
  this before committing, and a contract test checks it.
- **Free agents** (derived, never stored): `player WHERE is_active AND player_id NOT IN
  (roster_entry for the league)`.
- These rows are the league's original state. Tools never write here (FR-019, Constitution VII).

### player_status

| Column | Type | Rules |
|---|---|---|
| player_id | INTEGER FK → player | PK part |
| source | TEXT | PK part |
| as_of | DATE | PK part |
| status | TEXT NOT NULL | CHECK IN (`healthy`,`DTD`,`GTD`,`Q`,`O`,`SUSP`,`IL`,`IL+`,`NA`) |

The latest status for a player is the row with the greatest `as_of` (ties broken by source name).
A roster load writes one row per rostered player, dated with the load date.

## Audit

### load_run

| Column | Type | Rules |
|---|---|---|
| run_id | INTEGER PK | |
| source | TEXT NOT NULL | `nba_stats`, `roster_csv`, `fixture` |
| scope | TEXT NOT NULL | JSON text, e.g. `{"seasons":["2026-27"],"incremental":true}` |
| started_at, finished_at | TIMESTAMP | `finished_at` NULL while running |
| outcome | TEXT NOT NULL | CHECK IN (`running`,`succeeded`,`failed`,`rejected`) |
| rows_inserted, rows_updated | INTEGER NOT NULL DEFAULT 0 | Data tables only |
| report | TEXT | Error message or rejection report (e.g. unresolved roster rows with candidates) |

Every loader run writes exactly one row (FR-010). SC-003's "zero rows changed" applies to data
tables, not to `load_run`.

## Derived reads (core, not stored)

Every read below counts regular-season games only (`game.season_type = 'regular'`, FR-012). There
is no option to include other season types.

| Read | Definition | Spec |
|---|---|---|
| Last N games | Player's `player_game` rows joined to `game`, filtered to `season_type = 'regular'` and `game_date ≤ as_of`, ordered by `game_date DESC`, limited to N, crossing seasons. Returns `found` and `requested` | FR-020, FR-020a |
| Team games in range | For each date in range, the player's stint team; count that team's games with the given statuses (`final` for history, `scheduled` for upcoming) | FR-021 |
| Missed games | Team games (final) − appearances in the same range | FR-021, US3 |
| League snapshot | League, teams, managers, roster entries with slot, latest status | FR-022 |
| Free agents | See roster_entry | FR-019, FR-022 |
| Player search | Every word of `normalize(q)` must appear: `search_name LIKE '%w1%' AND …` | FR-023 |
