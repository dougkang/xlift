# Phase 0 Research: League Data Schema & NBA Stats Ingestion

All findings below were verified against `nba_api` 1.11.6 with live calls on 2026-10-23, unless
marked otherwise.

## R1. Which `nba_api` endpoints to use

**Decision**: Use four bulk endpoints. A full season takes about 4 requests.

| Need | Endpoint | Call shape |
|---|---|---|
| Box scores (FR-002, FR-006) | `LeagueGameLog` | `player_or_team_abbreviation='P'`, one call per season and season type; incremental via `date_from_nullable` |
| Schedule incl. future games (FR-011) | `ScheduleLeagueV2` | one call per season |
| Players: names, positions, current team, rookies with 0 games | `PlayerIndex` | one call per season |
| NBA teams | `nba_api.stats.static.teams` | offline static list, no request |

**Rationale**: SC-001 (full season < 30 min) is trivially met. Per-game `BoxScoreTraditionalV3`
would need about 1,230 requests per season (20+ minutes at a safe request rate) and more exposure to
rate limits.

**Observed facts** (live):

- **Player game log columns**: `LeagueGameLog` in player mode returns `PLAYER_ID, PLAYER_NAME,
  TEAM_ID, TEAM_ABBREVIATION, GAME_ID, GAME_DATE (YYYY-MM-DD), MATCHUP, MIN (int64), FGM, FGA, FG3M,
  FG3A, FTM, FTA, OREB, DREB, REB, AST, STL, BLK, TOV, PF, PTS, PLUS_MINUS` plus derived columns that
  we ignore (`*_PCT`, `FANTASY_PTS`).
- **No DNP rows**: the full 2025-26 regular season has 26,651 rows. All are appearances; DNPs are
  absent (see R3).
  - 83 rows have `MIN = 0`: appearances of a few seconds, rounded down. They count as games
    played, so the minutes CHECK is `>= 0`.
  - In the same data, these CHECKs have 0 violations: `REB = OREB + DREB`, made ≤ attempted for
    every shot type, no negative counts, `PLUS_MINUS` never null.
- **Schedule**: the 2026-27 schedule is already published (1,274 games). `gameStatus` is
  1 = scheduled, 2 = live, 3 = final. `postponedStatus` is `N`/`Y`.
  - **Status mapping**:
    - `postponedStatus = 'Y'` → `postponed`
    - otherwise 3 → `final`
    - 1 or 2 → `scheduled`; a live game stays `scheduled` and gets no box scores until it is
      final, so a refresh during games is safe. `gameDateEst` is ISO 8601;
  `gameDate` is `MM/DD/YYYY 00:00:00` and is not used.
- **Players**: `PlayerIndex(season='2026-27')` returns 519 rostered players, including rookies
  with no games (e.g. AJ Dybantsa, WAS). It gives `POSITION` (`G`, `F`, `C`, `G-F`, `F-C`, …) and
  `TEAM_ID`. Names keep suffixes (`Jimmy` / `Butler III`).

**Alternatives considered**:

- `BoxScoreTraditionalV3` per game: it would list DNPs with comments, but costs about 300 times more
  requests. Kept as a possible later upgrade if injury reasons are ever needed.
- `CommonAllPlayers`: has no positions. Rejected in favor of `PlayerIndex`.

## R2. Season types

**Decision**: Map from the 3-digit prefix of the game ID. `001` → `preseason`, `002` →
`regular`, `003` → `all_star`, `004` → `playoffs`, `005` → `play_in`, `006` → `cup_final`.
Only `regular` games are loaded, and only `regular` games are read (FR-012). Other prefixes are
mapped so they can be recognized and skipped.

**Rationale**: Verified in the live 2026-27 schedule. `002` covers 1,206 games, including NBA Cup
group and knockout games, which count as regular season. `001` is preseason. `006` is the single
Cup final, which does not count toward regular-season stats. The `004` and `005` prefixes
follow the same NBA convention but cannot be checked until the playoffs are scheduled.

**Alternatives considered**: `gameSubtype` / `gameLabel` are marketing labels ("AWS NBA Rivals
Week", "NBA Paris Game") and do not reliably give the season type. Rejected.

## R3. Missed games and which team a player belonged to (FR-021, injury-proneness)

**Decision**:

- `player_game` stores appearances only. There are no `played = false` rows, so a missed game can
  never look like a zero-production game (spec edge case).
- A new `player_team_stint` table records the date ranges a player belonged to an NBA team. The
  NBA stats adapter derives it as follows:
  - Each run of consecutive appearances for the same team becomes a stint.
  - A player's first stint of a season starts on the season's first regular-season date, so games
    missed before their first appearance count as missed. Each later stint starts on its first
    appearance.
  - A stint ends the day before the next stint starts.
  - The current team from `PlayerIndex` gets an open-ended stint:
    - If the player has appearances for that team, the stint is the run that includes them.
    - If they have no appearances for it (traded while injured, or injured or a rookie all
      season), it starts the day after their last appearance for their previous team, or at
      season start if they have no appearances at all.
  - The result never has overlapping stints; a contract test checks this.
- Availability for player P over [start, end]:
  - team games = final games of the team P was on (by stint) on each game date
  - played = P's appearances in that range
  - missed = team games − played
- Future (scheduled) games use the open-ended current stint.

**Rationale**: The game log has no DNP rows (R1). The stint is a source-neutral concept: any other
provider can fill it, so Principle VI holds. The trade-gap rule (missed games between teams count
against the old team) is an approximation. Its error is limited to the days around a trade.

**Alternatives considered**:

- Infer the team from the nearest appearance at query time. Rejected: it cannot handle players
  with no appearances on their current team, and it puts source-shaped heuristics into core.
- Per-game box scores with DNP flags (R1). Rejected for cost.

## R4. Incremental, idempotent loads (FR-007, FR-008, SC-003)

**Decision**:

- The incremental box score load requests `date_from = (latest final game date in the DB for that
  season) − 3 days`. The 3-day overlap picks up the NBA's stat corrections.
- Every write is an upsert keyed on natural keys (`game_id`, `(game_id, player_id)`, …). The
  `DO UPDATE` runs only when a value actually differs
  (`ON CONFLICT … DO UPDATE … WHERE <any column IS DISTINCT>`), so a no-op rerun changes zero data
  rows.
- Each game's box score rows and its game status update are written in one transaction. A crash
  leaves each game either fully present or unchanged.
- `load_run` always gets a row. **SC-003 applies to data tables only.** The spec was updated to say
  so.

**Rationale**: This meets FR-007 and FR-008 without a staging area. Holding one transaction per
game, or per batch of games for speed with all of a game's rows in the same batch, keeps the
"game is either complete or absent" guarantee.

**Alternatives considered**: Truncate and reload a season on every run. Rejected: it breaks
SC-003, and it leaves a window where data is missing.

## R5. Request pacing and retries (FR-009)

**Decision**: Wrap every endpoint call in a client that:

- waits at least 1.0 s between requests and sets `timeout=30`
- retries `ReadTimeout`, `ConnectionError`, and HTTP 429/5xx with exponential backoff (2, 4, 8,
  16, 32 s; max 5 attempts)
- fails the whole load run after the final attempt

Stats.nba.com blocks some cloud and data-center IPs. The loader is meant to run from a home or
office network, and `quickstart.md` says so.

**Rationale**: About 4 requests per season makes pacing almost free. Retries handle the
intermittent timeouts that `nba_api` users commonly see.

## R6. Database access and migrations (FR-005, Principle VI)

**Decision**:

- **Access**: SQLAlchemy 2.x Core, using `text()` SQL with named parameters. No ORM. Core read
  functions are plain SQL against the contract.
- **Migrations**: ordered plain SQL files (`NNNN_<name>.sql`) applied by a small runner in the
  contract package. The runner records applied versions in `schema_migrations`. The current version
  is `SELECT MAX(version) FROM schema_migrations`.
- **Connection**: `FFMODEL_DB_URL`, default `sqlite:///data/ffmodel.sqlite` relative to the repo
  root. SQLite connections enable `PRAGMA foreign_keys = ON`.

**Rationale**: The SQL files are the contract, readable by anyone. SQLAlchemy Core gives
portable parameter binding and connection handling. Swapping SQLite for another engine is then a
URL change (constitution, Technology Stack).

**Alternatives considered**:

- Alembic: more machinery than a single-schema project needs, and its Python migration files
  hide the DDL. Revisit if the schema needs branching.
- stdlib `sqlite3`: its parameter style (`?`) and connection API are SQLite-only.

**Implementation note (2026-10-23)**: The upsert helper (`adapters/common.py`) ended up not
using `ON CONFLICT` at all. It reads the existing keys with a row-value `IN (VALUES …)` lookup,
then runs a plain `INSERT` for new rows and an `UPDATE` for changed rows. This is ISO SQL, so the
portability exception below no longer applies.

**Original portability note**: `INSERT … ON CONFLICT … DO UPDATE` is not ISO SQL, but SQLite and
PostgreSQL (9.5+) both support it with the same syntax. The no-op guard `IS DISTINCT FROM` needs
SQLite 3.39+. The SQLite bundled with uv's Python 3.12 is 3.50.4, and `schema.sql` was verified
through it. It is used only in adapters' write paths,
never in the DDL or in core reads. This is recorded in the plan's Complexity Tracking.

## R7. Name normalization, search, and roster matching (FR-016, FR-023)

**Decision**:

- **Normalization**: one `normalize_name()` in the contract package, used by both the roster
  adapter (for matching) and core (for search):
  - transliterate to ASCII with `anyascii`, lowercase
  - drop punctuation (`.`, `'`, `’`, `-` → space)
  - drop generational suffixes (`jr`, `sr`, `ii`, `iii`, `iv`, `v`)
  - collapse whitespace
- **Storage**: `player.search_name` holds the normalized full name. Search splits the normalized
  query into words and requires each one: `search_name LIKE '%' || :w1 || '%' AND …`. This works in SQLite and
  PostgreSQL.
- **Matching order** for each roster row:
  1. A user-confirmed `player_external_id` (`match_method = 'user'`) for (source, file player ID).
     Stored `auto` matches are not consulted.
  2. An exact normalized full-name match among active players, plus last season's players.
  3. An initial-plus-last-name match (`n alexander walker` ↔ `nickeil alexander walker`).
  4. If several candidates remain, keep the one whose current team matches the file's `nba_team`.
  5. Anything else is unresolved. The report lists the three nearest candidates by string
     similarity (`difflib`) with their player IDs.
- **Recording matches**: automatic matches are stored as `player_external_id` with
  `match_method = 'auto'`. They are recomputed on every load, and the stored row is updated if the
  match changes, so a wrong match never gets locked in. User resolutions are stored with `match_method = 'user'` and always
  win on later loads.

**Rationale**: Accent folding cannot be done portably inside SQL (SQLite has no folding
collation, and custom SQL functions are connection-specific). A stored normalized column keeps the
query portable. `anyascii` (ISC license) also handles letters that do not decompose under Unicode
normalization, such as `ł` and `ø`. `unidecode` was rejected because it is GPL.

Checked by hand against the reference file: `Luka Dončić`, `Alperen Şengün`, `Dennis Schröder`,
`Egor Dëmin`, `Nikola Vučević`, and `Jusuf Nurkić` all normalize to the NBA names.
`Jimmy Butler III` ↔ `Butler III` and `Bobby Portis Jr.` ↔ `Bobby Portis` match after suffix
removal. `N. Alexander-Walker` matches by initial.

## R8. Roster file semantics

**Decision**:

- **Status mapping**: blank → `healthy`. `Q`, `O`, `DTD`, `GTD`, `SUSP` are kept as-is; `IL`,
  `IL+`, and `NA` are reserve statuses. A roster entry's `slot` is `reserve` when its status is a
  reserve status, otherwise `active`. FR-017's capacity check counts `active` slots only. The
  reference file has 9–10 active players per team, so the default capacity of 10 passes.
- **Managers**: the file has no manager IDs, and the name "Paul" runs both `t.04` and `t.10`.
  Rule: **a manager is identified by (league, display name)**, so two teams with the same manager
  name share one manager row. `fantasy_team.manager_id` is not unique, so one manager can run
  several teams. If the two Pauls are different people, the user can rename one in the file;
  nothing else changes.
- **Atomic replace**: a roster load replaces the league's `roster_entry` rows in one transaction
  (FR-019). If any row is unresolved or invalid, nothing changes, and a `load_run` with outcome
  `rejected` and the full report is recorded.
- **External ID source**: the file's `player_id` values (`nba.p.*`) are stored under a
  source label given at load time. The default is `yahoo`, which is where that key format comes
  from.

## R9. Tooling

**Decision**:

- **Environment**: Python 3.12, managed with `uv` (`requires-python = ">=3.12"`). The system
  interpreter is 3.9.6 and is not used.
- **Runtime dependencies**: `nba_api`, `sqlalchemy>=2`, `anyascii`, `typer`.
- **Dev dependencies**: `pytest`, `import-linter`, `ruff`.
- **CLI**: Typer, exposed as the `ffm` entry point.
- **Layering**: `import-linter` contracts in `pyproject.toml` enforce Principle VI/VII import
  rules. `core` must not import `adapters`, and `adapters` must not import `core`. Both may import
  `contract`.
- **Tests**:
  - Adapter tests replay recorded `nba_api` JSON responses stored under `tests/fixtures/`. No
    network.
  - A `live` pytest marker covers the real-source checks (SC-001, SC-002, SC-004). These are
    excluded by default.

**Alternatives considered**: `argparse` instead of Typer. It would work; Typer was chosen because it
generates `--help` from type hints with less boilerplate.
