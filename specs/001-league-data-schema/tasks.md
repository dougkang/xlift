---

description: "Task list for League Data Schema & NBA Stats Ingestion"
---

# Tasks: League Data Schema & NBA Stats Ingestion

**Input**: Design documents from `specs/001-league-data-schema/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (schema.sql, read-api.md, cli.md, roster-csv.md), quickstart.md

**Tests**: Included. The constitution (Development Workflow & Quality Gates) requires schema contract tests and
fixture-based core tests. Spec FR-025 and SC-006 require a fixture dataset used by automated tests.
Within each story, write the tests first and confirm they fail before implementing.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on
its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story the task belongs to (US1–US4)
- All paths are relative to the repository root. Python code lives under `backend/` (plan.md,
  Project Structure).

## Conventions for every task

- Python 3.12 via `uv`. Run tools from `backend/`: `uv run pytest`, `uv run ruff check`,
  `uv run lint-imports`.
- DB access uses SQLAlchemy 2.x Core with `text()` and named parameters only. No ORM.
- Dates are stored as ISO-8601 TEXT `YYYY-MM-DD`. Booleans are INTEGER 0/1 (contracts/schema.sql).
- Layering (Constitution VI/VII):
  - `ffmodel.core` MUST NOT import `ffmodel.adapters` or `nba_api`.
  - `ffmodel.adapters` MUST NOT import `ffmodel.core`.
  - `ffmodel.contract` imports neither.
  - Only `ffmodel/cli.py` may import both adapters and core.
- Tests never touch the network unless marked `@pytest.mark.live`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, dependencies, tooling

- [X] T001 Create the directory skeleton and package files from plan.md:
  - Packages, each with an empty `__init__.py`:
    - `backend/src/ffmodel/`
    - `backend/src/ffmodel/contract/` (and its `migrations/` directory)
    - `backend/src/ffmodel/adapters/`, `adapters/nba_stats/`, `adapters/roster_csv/`
    - `backend/src/ffmodel/core/`, `core/data/`
  - Test directories: `backend/tests/{contract,unit,integration,integration/live,fixtures,fixtures/nba_api,fixtures/rosters}/`
  - `data/.gitkeep` at the repo root.
  - A root `.gitignore` containing `data/*.sqlite*`, `.venv/`, `__pycache__/`, `.pytest_cache/`,
    `.ruff_cache/`.
- [X] T002 Create `backend/pyproject.toml` as a uv project:
  - Project: name `ffmodel`, `requires-python = ">=3.12"`, src layout (`[tool.uv]` / hatchling
    with packages `src/ffmodel`).
  - Dependencies: `nba_api>=1.11,<2`, `sqlalchemy>=2.0,<3`, `anyascii>=0.3`, `typer>=0.12`.
  - Dev dependency group: `pytest>=8`, `import-linter>=2`, `ruff>=0.6`.
  - Script: `ffm = "ffmodel.cli:app"`.
  - `[tool.pytest.ini_options]`:
    - `testpaths = ["tests"]`
    - `markers = ["live: hits the real NBA stats source (manual)"]`
    - `addopts = "-m 'not live'"`
  - `[tool.ruff]`: `line-length = 100`, `target-version = "py312"`.
  - Then run `uv sync` in `backend/`.
- [X] T003 [P] Create `backend/.importlinter` with `root_package = ffmodel` and three `forbidden`
  contracts. Ignore `ffmodel.cli` in each.
  1. Sources `ffmodel.core` may not import `ffmodel.adapters` or `nba_api`.
  2. Sources `ffmodel.adapters` may not import `ffmodel.core`.
  3. Sources `ffmodel.contract` may not import `ffmodel.adapters` or `ffmodel.core`.
- [X] T004 [P] Create `backend/tests/conftest.py` with:
  - An autouse fixture that blocks network access by monkeypatching `socket.socket.connect` to
    raise `RuntimeError("network disabled in tests")`, unless the test has the `live` marker.
  - A fixture `engine` that creates a temp-file SQLite engine through
    `ffmodel.contract.db.get_engine(f"sqlite:///{tmp_path}/t.sqlite")` and applies migrations
    with `ffmodel.contract.migrate.migrate(engine)`. It depends on T006 and T007; import lazily
    inside the fixture.
  - A fixture `fixture_engine` that is `engine` plus `tests.fixtures.dataset.load_fixture(conn)`
    (T014).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The contract package (schema, migrations, connection, name normalization), shared
adapter helpers, read-model types, and the fixture dataset. Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Create `backend/src/ffmodel/contract/migrations/0001_initial.sql` as a byte-for-byte copy
  of `specs/001-league-data-schema/contracts/schema.sql`. It holds all 15 tables, every CHECK,
  UNIQUE and index. Do not edit the DDL; the spec's contract is the source.
- [X] T006 Implement `backend/src/ffmodel/contract/db.py`:
  - `default_db_url()` returns `os.environ.get("FFMODEL_DB_URL")`. Otherwise it returns
    `sqlite:///<repo_root>/data/ffmodel.sqlite`, where `repo_root` is found by walking up from
    this file to the directory that contains `backend/`.
  - `get_engine(url: str | None = None) -> Engine`:
    - Creates the parent directory for SQLite file URLs.
    - Registers a `connect` event listener that runs `PRAGMA foreign_keys = ON` for SQLite.
- [X] T007 Implement `backend/src/ffmodel/contract/migrate.py`:
  - `migrate(engine) -> list[int]`:
    - Creates `schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT
      NOT NULL)` if it is missing.
    - Discovers `migrations/NNNN_*.sql` through `importlib.resources`, sorted by NNNN.
    - Applies each unapplied file in its own transaction. Split statements on `;` at line end, or
      use `conn.connection.executescript` for SQLite.
    - Returns the versions it applied.
  - `current_version(engine) -> int` returns `MAX(version)`, or 0.
- [X] T008 [P] Implement `backend/src/ffmodel/contract/names.py` (research R7):
  - `normalize_name(s: str) -> str`:
    1. `anyascii(s)`, then lowercase.
    2. Replace `.`, `'`, `’`, `-`, `,` with a space.
    3. Drop the tokens `jr`, `sr`, `ii`, `iii`, `iv`, `v`.
    4. Collapse whitespace and strip.
  - `name_words(s: str) -> list[str]` returns `normalize_name(s).split()`.
- [X] T009 [P] Write `backend/tests/unit/test_names.py`, a parametrized test that asserts
  `normalize_name`:
  - `"Luka Dončić"` → `"luka doncic"`
  - `"Alperen Şengün"` → `"alperen sengun"`
  - `"Dennis Schröder"` → `"dennis schroder"`
  - `"Egor Dëmin"` → `"egor demin"`
  - `"Nikola Vučević"` → `"nikola vucevic"`
  - `"Jimmy Butler III"` → `"jimmy butler"`
  - `"Bobby Portis Jr."` → `"bobby portis"`
  - `"N. Alexander-Walker"` → `"n alexander walker"`
  - `"Day'Ron Sharpe"` → `"day ron sharpe"`
  - `"Kel'el Ware"` → `"kel el ware"`
- [X] T010 [P] Write `backend/tests/contract/test_schema.py`, using the `engine` fixture.
  - **Migrations**:
    - `migrate` on an empty DB applies `[1]`.
    - `current_version == 1`.
    - A second `migrate` applies `[]`.
  - **Constraints**: one test per rule, each inserting a minimal violating row and asserting
    `IntegrityError`:
    - `season.season_id` length ≠ 7; `end_date < start_date`.
    - Duplicate `nba_team.abbreviation`.
    - `player.is_active` not in (0, 1).
    - `player_external_id.match_method` not in (`'exact'`,`'auto'`,`'user'`); duplicate
      `(source, external_id)`.
    - `game.season_type` outside (`'preseason'`,`'regular'`,`'all_star'`,`'playoffs'`,`'play_in'`,
      `'cup_final'`).
    - `game.status` outside (`'scheduled'`,`'final'`,`'postponed'`,`'cancelled'`);
      `home_team_id = away_team_id`.
    - `player_game` box-score rules:
      - `minutes < 0`; `fga < fgm`; `fg3m > fgm`; `fg3a < fg3m`; `fg3a > fga`; `fta < ftm`
      - `reb <> oreb + dreb`; any negative count
      - duplicate `(game_id, player_id)`
    - `player_team_stint.end_date < start_date`.
    - `fantasy_league.active_roster_capacity <= 0`; duplicate `league_key`.
    - Duplicate `manager (league_id, display_name)`; duplicate
      `fantasy_team (league_id, source_team_key)`.
    - `roster_entry.slot` not in (`'active'`,`'reserve'`); the same player twice in one league
      (PK `(league_id, player_id)`).
    - `player_status.status` outside (`'healthy'`,`'DTD'`,`'GTD'`,`'Q'`,`'O'`,`'SUSP'`,`'IL'`,
      `'IL+'`,`'NA'`).
    - `load_run.outcome` outside (`'running'`,`'succeeded'`,`'failed'`,`'rejected'`).
    - A foreign key to a missing parent row (proves `PRAGMA foreign_keys` is on).
  - **Drift check**: `0001_initial.sql` equals `specs/001-league-data-schema/contracts/schema.sql`.
- [X] T011 [P] Write `backend/tests/contract/test_layering.py`. It runs
  `subprocess.run(["lint-imports"], cwd=<backend dir>)` and asserts exit code 0 (Constitution VI).
- [X] T012 [P] Write `backend/tests/invariants.py` with `assert_contract_invariants(conn)`, called by
  the US1/US2 integration tests and by T050. It asserts:
  1. No two `player_team_stint` rows for the same player overlap (an open `end_date` counts as
     infinity).
  2. Every `player_game.team_id` is that game's `home_team_id` or `away_team_id`.
  3. Every `player_game` row belongs to a game with `status = 'final'`.
  4. Per `fantasy_team`, the count of `slot = 'active'` ≤ the league's `active_roster_capacity`.
  5. Every `roster_entry.fantasy_team_id` belongs to the same `league_id`.
- [X] T013 Implement `backend/src/ffmodel/adapters/common.py`, the shared write helpers for both
  adapters:
  - `upsert(conn, table: str, key_cols: Sequence[str], rows: Sequence[Mapping]) -> tuple[int, int]`
    returns (inserted, updated).
    - It looks up which keys already exist, then runs
      `INSERT … ON CONFLICT (<keys>) DO UPDATE SET c = excluded.c, … WHERE <t.c IS DISTINCT FROM
      excluded.c OR …>`.
    - It counts updates by comparing the existing rows to the new values, so an identical rerun
      reports (0, 0) (SC-003, research R4).
  - `start_run(engine, source, scope: dict) -> int`: inserts a `load_run` row with
    `outcome='running'` and `started_at = now UTC ISO`, in its own committed transaction, so the
    row survives a data rollback.
  - `finish_run(engine, run_id, outcome, inserted, updated, report=None)`: sets `finished_at`.
  - `ensure_external_id(conn, table, source, external_id, entity_col, entity_id, match_method=None)`.
- [X] T014 Create `backend/tests/fixtures/dataset.py` with `load_fixture(conn)` and the constant
  `FIXTURE_TODAY = date(2026, 10, 30)`. It writes deterministic rows with plain SQL through the
  contract (FR-025), using source `fixture` and fixed internal IDs. Rows:
  - **Seasons**: `2025-26` (2025-10-21 → 2026-04-12) and `2026-27` (2026-10-20 → 2027-04-11).
  - **Teams**: 1 LAL, 2 ATL, 3 GSW, 4 WAS, 5 DAL.
  - **Players**: `full_name`, `search_name = normalize_name(full_name)`, positions, current team,
    `is_active`.
    1. Luka Dončić (LAL, `G,F`)
    2. Nickeil Alexander-Walker (ATL, `G`)
    3. Jimmy Butler III (GSW, `F`)
    4. Bobby Portis (WAS, `F,C`)
    5. AJ Dybantsa (WAS, `F`)
    6. Trey Tradeson (ATL, `F`)
    7. Old Vet (`current_team NULL`, `is_active=0`)
    8. Iggy Injured (GSW, `G`)
    9. Dennis Schröder (DAL, `G`)
    10. Marcus Twin (LAL, `G`)
    11. Marcus Twin (GSW, `F`)
    12. Free Agent Fred (DAL, `C`)
  - **Games**: an explicit list, not generated by a round-robin. All are `season_type='regular'`
    unless noted otherwise.
    - **2025-26 (LAL only)**: 72 `final` games, numbered k = 0…71. Game k is on 2025-10-21 + 2k
      days, so the last is on 2026-03-12.
      - The opponent is `[ATL, GSW, WAS, DAL][k % 4]`, so LAL plays 18 games against each team.
      - LAL is home when k is even.
      - Examples: k = 51 is 2026-01-31 vs DAL; k = 55 is 2026-02-08 vs DAL; k = 56 is 2026-02-10
        vs ATL.
    - **2026-27 finals** (through 2026-10-29):

      | # | Date | Home | Away |
      |---|---|---|---|
      | G1 | 10-20 | LAL | GSW |
      | G2 | 10-21 | WAS | DAL |
      | G3 | 10-22 | GSW | ATL |
      | G4 | 10-23 | LAL | WAS |
      | G5 | 10-24 | GSW | DAL |
      | G6 | 10-25 | ATL | WAS |
      | G7 | 10-26 | LAL | DAL |
      | G8 | 10-27 | GSW | WAS |
      | G9 | 10-28 | LAL | ATL |

      Totals: LAL 4 (G1, G4, G7, G9), GSW 4 (G1, G3, G5, G8), WAS 4, DAL 3, ATL 3.
    - **2026-27 upcoming** (2026-10-31 → 2026-11-08):

      | # | Date | Home | Away | Status |
      |---|---|---|---|---|
      | S1 | 10-31 | LAL | ATL | `scheduled` |
      | S2 | 11-01 | GSW | DAL | `scheduled` |
      | S3 | 11-02 | GSW | WAS | `postponed` |
      | S4 | 11-03 | LAL | GSW | `scheduled` |
      | S5 | 11-05 | GSW | ATL | `cancelled` |
      | S6 | 11-06 | WAS | LAL | `scheduled` |
      | S7 | 11-08 | GSW | DAL | `scheduled` |

      GSW has 3 countable scheduled games in this range (S2, S4, S7).
    - **Never counted** (FR-012), all `final`, all with a Dončić box score:
      - `preseason` 2026-10-10, LAL vs ATL
      - `play_in` 2026-04-15, LAL vs ATL
      - `playoffs` 2026-04-19, LAL vs GSW
  - **Box scores** (`player_game`): valid stat lines that satisfy every CHECK, and are not all
    zeros.
    - **Dončić**:
      - 2025-26: every LAL game except k = 10 and k = 11, so exactly 70 games.
      - 2026-27: G1, G4, G7, G9.
      - The three never-counted games above.
    - **Dybantsa (WAS)**: G2, G4, G6 (3 games; misses G8). No 2025-26 games.
    - **Iggy Injured (GSW)**: G3 and G8 only. He misses G1 and G5, so his team played 4, he played
      2, and he missed 2.
    - **Trey Tradeson**:
      - DAL: every LAL-vs-DAL game with k ≤ 51 (k = 3, 7, …, 51, so 13 games). He misses k = 55
        (2026-02-08).
      - ATL: every LAL-vs-ATL game with k ≥ 56 (k = 56, 60, 64, 68, so 4 games).
    - **Old Vet (LAL)**: LAL games k = 0…29 (30 games, last on 2025-12-18). No 2026-27 games.
    - **Players 2, 3, 4, 9, 10, 11, 12**: 2–3 games each, taken from games their team plays in
      the lists above.
  - **Stints**: consistent with research R3.
    - **Tradeson**: DAL 2025-10-21 → 2026-02-09, then ATL 2026-02-10 → open. The ATL stint
      starts at his first ATL appearance.
    - **Old Vet**: LAL 2025-10-21 → 2025-12-18, closed at his last appearance because his current
      team is NULL.
    - **Everyone else**: one stint per season, starting at season start.
      - A 2025-26 stint ends at 2026-04-12, the season end.
      - The 2026-27 stint is open (NULL `end_date`) for the player's current team.
  - **League**: `fantasy_league` `league_key='fixture-league'`, season `2026-27`,
    `scoring_format_id='9cat_h2h'`, capacity 3.
    - Managers: "Ann" and "Bo".
    - `t.01` "Alpha" (Ann): Dončić active, Butler active, Dybantsa active, Iggy reserve.
    - `t.02` "Beta" (Bo): Alexander-Walker active, Schröder active.
  - **Status** (`player_status`, `source='fixture'`, `as_of=2026-10-29`): Iggy `IL`, Butler `Q`,
    others `healthy`.
  - **External IDs**: `player_external_id` rows `fixture:<n>` with `match_method='exact'` for
    every player.
- [X] T015 [P] Implement `backend/src/ffmodel/core/data/models.py` with the frozen dataclasses
  exactly as in `contracts/read-api.md`:
  - `PlayerSummary`
  - `PlayerGameLine`
  - `GameWindow`, with property `is_short = found < requested`
  - `Availability`, with property `games_missed = team_games - games_played`
  - `LeagueSettings`, `LeagueSnapshot`, `FantasyTeamView`, `RosterPlayer`

  Also create `backend/src/ffmodel/core/data/__init__.py`, which re-exports the models now and the
  read functions as they are added in later stories.
- [X] T016 Write `backend/tests/contract/test_fixture.py`:
  - `load_fixture` succeeds on a migrated DB.
  - `assert_contract_invariants` passes.
  - Every table has at least one row except `load_run` and `game_external_id`.

**Checkpoint**: The contract is migrated and tested, the fixture loads, and the layering lint
passes. The user stories can now start in parallel.

---

## Phase 3: User Story 1 - Load NBA player game history (Priority: P1) 🎯 MVP

**Goal**: One command fills the NBA side of the contract (teams, players, schedule, box scores,
stints) from `nba_api`, incrementally and idempotently (FR-006–FR-013).

**Independent Test**: Replaying recorded responses into an empty DB produces the expected rows.
A rerun changes 0 data rows. A player traded mid-season shows the correct team per game.
Live: `ffm load nba` for one season matches the official game log of a chosen player.

### Tests for User Story 1

- [X] T017 [P] [US1] Create `backend/tests/fixtures/nba_api/record.py`, a manual script run once
  with network access. It saves trimmed raw JSON responses
  (`endpoint.get_dict()`) to `backend/tests/fixtures/nba_api/`:
  - `leaguegamelog_P_2025-26_2026-01-15.json`: player mode, regular season, date range
    2026-01-15 to 2026-01-15.
  - `leaguegamelog_P_2025-26_2026-01-16.json`.
  - `scheduleleaguev2_2025-26.json`: trimmed to games on 2026-01-15/16, plus 3 future-dated
    sample games with `gameStatus=1`, one with `gameStatus=2`, and one with
    `postponedStatus='Y'`. Edit statuses by hand if needed.
  - `playerindex_2025-26.json`: trimmed to the players appearing in the two logs.

  Commit the JSON files. Tests load them through a fake client (T018).
- [X] T018 [P] [US1] Create `backend/tests/fixtures/nba_api/fake_client.py` with `FakeNbaStatsClient`.
  - It implements the same interface as `NbaStatsClient` (T024): `game_log`, `schedule`,
    `player_index`.
  - It serves the recorded JSON from T017 and filters game logs by `date_from`.
  - It counts calls.
  - It can be told to raise after K box-score rows, for the partial-write test.
- [X] T019 [P] [US1] Write `backend/tests/unit/test_nba_mapping.py`, covering the functions in
  `adapters/nba_stats/mapping.py`:
  - **`season_type_from_game_id`**: `0012600009`→`preseason`, `0022500585`→`regular`,
    `003…`→`all_star`, `004…`→`playoffs`, `005…`→`play_in`, `0062600001`→`cup_final`. Any other
    prefix raises `ValueError`.
  - **`game_status`**: `(3,'N')`→`final`, `(1,'N')`→`scheduled`, `(2,'N')`→`scheduled`,
    `(1,'Y')`→`postponed`, `(3,'Y')`→`postponed`.
  - **`normalize_positions`**: `G`→`G`, `G-F`→`G,F`, `F-G`→`G,F`, `C-F`→`F,C`, `F-C`→`F,C`, `''`→None.
    Output order is always G, F, C.
  - **`season_from_season_id`**: `"22025"`→`"2025-26"`.
  - **`season_label`**: `2026`→`"2026-27"`; `2099`→`"2099-00"`.
  - **`current_season`**: `current_season(date(2026,10,23))`→`"2026-27"`;
    `current_season(date(2027,3,1))`→`"2026-27"`; `current_season(date(2026,8,1))`→`"2025-26"`.
    The new season label starts in October.
  - **`box_score_row`**: maps a `LeagueGameLog` row to `player_game` columns. `MIN` is converted to
    float; `*_PCT` and `FANTASY_PTS` are dropped.
- [X] T020 [P] [US1] Write `backend/tests/unit/test_stints.py` for `derive_stints(appearances,
  season_start, current_team_id, season_end=None)`. `appearances` is a list of (game_date, team_id) for one player
  and one season. Cases:
  1. One team all season → one stint from `season_start`, open.
  2. First appearance on day 40 → the stint still starts at `season_start`, so games missed before
     the debut count.
  3. Trade A→B with last A game on d1 and first B game on d2 → A: [season_start, d2−1], then
     B: [d2, open].
  4. Traded while injured: appearances only for A, `current_team_id = B` → A: [season_start,
     last_A], then B: [last_A + 1 day, open].
  5. No appearances, current team C → C: [season_start, open].
  6. `current_team_id = None` (released or retired) → the last stint is closed at its last
     appearance.
  7. Season-end close: a season that is not the newest loaded is called with a `season_end` and
     `current_team_id` unused, and its last stint closes at `season_end`.

  Every case also asserts that no stints overlap.
- [X] T021 [P] [US1] Write `backend/tests/unit/test_nba_client.py` for `NbaStatsClient`, with an
  injected fake endpoint callable and a fake `sleep`/`monotonic`:
  - Calls are at least 1.0 s apart.
  - `ReadTimeout`, `ConnectionError`, and HTTP 429/5xx are retried with backoff 2, 4, 8, 16, 32 s
    (max 5 attempts) and then raise `SourceUnavailable`.
  - A non-retryable error (e.g. HTTP 400) raises immediately.
  - Every endpoint call gets `timeout=30`.
- [X] T022 [US1] Write `backend/tests/integration/test_nba_loader.py`, using `engine` +
  `FakeNbaStatsClient`. Each scenario calls `load_nba(engine, seasons=["2025-26"], client=fake)`.
  1. **First load**: row counts for `nba_team`, `player`, `game`, and `player_game` match the
     recorded JSON. `load_run` has one `succeeded` row with non-zero inserted.
     `assert_contract_invariants` passes.
  2. **Rerun** (US1-2, SC-003): a checksum of every data table is unchanged, and the second
     `load_run` reports `rows_inserted = 0` and `rows_updated = 0`.
  3. **Incremental** (US1-3): after seeding only the 01-15 log, a load with the 01-16 log present
     requests `date_from = 2026-01-12` (latest final 01-15 − 3 days) and adds only the 01-16 rows.
  4. **Stat correction**: altering one PTS value in the fake response → `rows_updated = 1`.
  5. **Partial write** (FR-008): the fake raises mid-game. That game has either all its
     `player_game` rows or none, `load_run.outcome = 'failed'` with `report` set, and a rerun
     completes the load.
  6. **Traded player** (US1-4): two log rows for one player with different `TEAM_ID` on different
     dates → each `player_game.team_id` matches, and stints are derived per T020.
  7. **Live and postponed games**: schedule rows with `gameStatus=2` are stored as `scheduled`
     with no box scores; rows with `postponedStatus='Y'` are stored as `postponed`.
  8. **External IDs**: `player_external_id(source='nba_stats', match_method='exact')`, plus
     `game_external_id` and `nba_team_external_id` rows, exist for loaded entities.
- [X] T023 [P] [US1] Write `backend/tests/integration/live/test_live_nba.py`. All tests carry
  `@pytest.mark.live` and use a temp DB.
  - **SC-001**: a full `load_nba(seasons=[current_season()])` finishes in under 30 min. An
    immediate incremental rerun finishes in under 5 min and changes 0 data rows.
  - **SC-002**: for 20 random players with at least 10 games, the summed `player_game` totals for
    FGM, FGA, FG3M, FG3A, FTM, FTA, OREB, DREB, REB, AST, STL, BLK, TOV, PF and PTS equal
    `LeagueDashPlayerStats(per_mode_detailed='Totals')` for the season.
  - **SC-004**: per-team scheduled game counts for the next 7 days equal counts computed directly
    from `ScheduleLeagueV2`. This proves the load matches its source. T050 adds a manual check
    against the official NBA.com schedule.

### Implementation for User Story 1

- [X] T024 [P] [US1] Implement `backend/src/ffmodel/adapters/nba_stats/client.py`, per research R5:
  - `NbaStatsClient(min_interval=1.0, timeout=30, sleep=time.sleep, clock=time.monotonic)`
  - Methods:
    - `game_log(season, date_from=None) -> list[dict]` wraps
      `leaguegamelog.LeagueGameLog(player_or_team_abbreviation='P', season_type_all_star="Regular Season",
      date_from_nullable=…)`.
    - `schedule(season) -> list[dict]` wraps `scheduleleaguev2.ScheduleLeagueV2`, `SeasonGames`.
    - `player_index(season) -> list[dict]` wraps `playerindex.PlayerIndex`.
  - The paced retry wrapper raises `SourceUnavailable` once retries are exhausted.
  - Regular season only (FR-012). There is no season-type parameter.
  - `cup_final` box scores are not fetched in this feature. Games still come from the schedule.
- [X] T025 [P] [US1] Implement `backend/src/ffmodel/adapters/nba_stats/mapping.py`: the pure
  functions specified in T019. The season-type prefix map is `{"001": "preseason", "002":
  "regular", "003": "all_star", "004": "playoffs", "005": "play_in", "006": "cup_final"}`.
  - `schedule_game_row(sg)` takes `game_date` from `gameDateEst[:10]` (ISO), and home/away from
    `homeTeam_teamId` / `awayTeam_teamId`.
  - Status mapping:
    - `postponedStatus == 'Y'` → `postponed`
    - otherwise `gameStatus` 3 → `final`
    - 1 or 2 → `scheduled`
- [X] T026 [P] [US1] Implement `backend/src/ffmodel/adapters/nba_stats/stints.py` with
  `derive_stints(...) -> list[Stint]`. It must satisfy every T020 case; research R3 has the rules.
- [X] T027 [US1] Implement `backend/src/ffmodel/adapters/nba_stats/loader.py`:
  `load_nba(engine, seasons=None, full=False, client=None,
  today=None) -> LoadSummary`. The default seasons are `[current_season(today), previous]`. Steps:
  1. `start_run('nba_stats', scope)`.
  2. Upsert `nba_team` from `nba_api.stats.static.teams`, plus `nba_team_external_id(source=
     'nba_stats')`.
  3. Per season, oldest first:
     1. Fetch `schedule`.
     2. Upsert `season`. The start and end dates are the min and max `game_date` of `regular`
        games.
     3. Fetch `player_index` and upsert `player` with `search_name = normalize_name(full_name)`.
        Only the newest requested season sets `current_team_id`, `is_active`, and `positions`.
        Older seasons only insert players that are missing.
     4. Upsert `game` for each schedule row whose game ID maps to `regular`, plus
        `game_external_id`. Skip every other season type (FR-012).
  4. Box scores: per season and season type, `date_from = None if full else (max game_date of
     final games with box scores in that season) − 3 days`. Then:
     1. Fetch `game_log`.
     2. Group rows by `GAME_ID`.
     3. Upsert each game's `player_game` rows inside one transaction per game (FR-008). Batching
        several games per transaction is allowed, but never splits a game.
     4. Skip rows whose game isn't `final`.
     5. If a log row's player is missing from `player`, insert it from the log's `PLAYER_NAME`
        with `is_active=0`.
  5. Recompute stints with `derive_stints` for every player touched in the season. Pass
     `current_team_id` only for the newest loaded season; older seasons pass `season_end` instead
     (T020 case 7). Upsert them
     and delete only stale stints, so a rerun changes nothing.
  6. `finish_run` with the totals, or with `failed` and the message on any exception (re-raise).
- [X] T028 [US1] Implement `backend/src/ffmodel/cli.py`, the Typer `app`, per `contracts/cli.md`:
  - **Commands**:
    - `db migrate` and `db version`
    - `load nba` with repeatable `--season`, plus `--full` (no season-type option; FR-012)
    - `runs` with `--limit`, default 10
  - **Options**: a global `--json` flag.
  - **Exit codes**: 0 on success, 1 on failure.
  - **Output**: a per-table summary on stdout and errors on stderr.
  - `cli.py` is the only module that may import both `ffmodel.adapters` and `ffmodel.core`.

**Checkpoint**: `uv run pytest tests/unit tests/integration/test_nba_loader.py` passes.
`uv run ffm db migrate && uv run ffm load nba --season 2025-26` works on a residential network.

---

## Phase 4: User Story 2 - Load my fantasy league from a roster file (Priority: P1)

**Goal**: Load a Yahoo-style roster CSV into a league, with tolerant name matching, remembered
user resolutions, atomic replace, status snapshots, and reserve slots (FR-014–FR-019, FR-022).

**Independent Test**: With the fixture DB:
- a valid synthetic CSV creates the league, its teams and its rosters
- an unresolvable row exits with 2 and writes nothing
- `roster resolve` followed by a reload succeeds
- free agents exclude every rostered player

### Tests for User Story 2

- [X] T029 [P] [US2] Create synthetic roster CSVs in `backend/tests/fixtures/rosters/`. Use the
  header `team_id,player_id,name,positions,nba_team,status,team_name,manager` and fixture players
  from T014.
  - **`valid.csv`**:
    - Team `t.01` "Keyboard Cats", manager "Doug":
      - `y.1` "Luka Doncic" LAL, no accents
      - `y.3` "Jimmy Butler" GSW, no suffix, status `Q`
      - `y.8` "Iggy Injured" GSW, status `IL`
    - Team `t.02` "Elsie’s World", manager "Paul":
      - `y.2` "N. Alexander-Walker" ATL
      - `y.9` "Dennis Schröder" DAL
      - `y.10` "Marcus Twin" LAL (tie broken by team)
      - `y.5` "AJ Dybantsa" WAS, status `NA`
    - Team `t.03` "Other Paul", manager "Paul": `y.4` "Bobby Portis Jr." WAS
  - **`unresolved.csv`**: `valid.csv` plus a row on team `t.03` ("Other Paul", manager "Paul"):
    `y.99` "Zed Nobody" BOS, blank status. `t.03` then has 2 active players, under capacity 3.
  - **`over_cap.csv`**: `t.01` with 4 active players at capacity 3.
  - **`duplicate.csv`**: `y.1` on both `t.01` and `t.02`.
  - **`inconsistent_team.csv`**: two `t.01` rows with different `team_name`.
  - **`bad_status.csv`**: one row with status `XYZ`.
  - **`ambiguous.csv`**: "Marcus Twin" with blank `nba_team`.
- [X] T030 [P] [US2] Write `backend/tests/unit/test_roster_parse.py` for `parse_roster_csv(path)`:
  - It handles quoted positions such as `"G,FC"`, UTF-8 curly apostrophes, and emoji team names.
  - Status mapping: blank → `healthy`. `IL`, `IL+` and `NA` give `slot='reserve'`. `Q`, `O`,
    `DTD`, `GTD` and `SUSP` give `slot='active'`.
  - It collects (rather than stops at) the first error for each rejection rule 1, 2 and 6 in
    `contracts/roster-csv.md`.
- [X] T031 [P] [US2] Write `backend/tests/unit/test_roster_match.py` for `match_rows(conn, rows,
  source)` against the fixture DB, covering the research R7 order:
  1. A confirmed `user` external ID wins, even over an exact name match to a different player.
     A stored `auto` row pointing to the wrong player is ignored, and the name match is recomputed.
  2. Exact normalized name.
  3. Initial plus last name (`N. Alexander-Walker`).
  4. Team tie-break (`Marcus Twin` LAL vs GSW).
  5. Ambiguous with no team → unresolved, with both twins as candidates.
  6. `Zed Nobody` → unresolved, with up to 3 `difflib` candidates that each carry an internal
     `player_id`.
- [X] T032 [US2] Write `backend/tests/integration/test_roster_loader.py` (fixture DB, Typer
  `CliRunner` for exit codes).
  - Each numbered scenario is its own test function on a fresh `fixture_engine`, so no state
    carries over.
  - Assert `assert_contract_invariants` after each success.
  1. **US2-1**: `valid.csv` with `--league-key cats --capacity 3` creates 3 teams. "Paul" is one
     `manager` row used by `t.02` and `t.03`, per research R8.
  2. **US2-2**: the auto matches are stored as `player_external_id(source='yahoo',
     match_method='auto')`.
  3. **US2-3**: `unresolved.csv` exits with 2, data tables are unchanged, and
     `load_run.outcome='rejected'` with a report that names row and `y.99`. Then
     `ffm roster resolve --source yahoo y.99 12` (Free Agent Fred) and a reload exits 0, and a
     third load prompts nothing.
  4. **US2-4**: `get_free_agents` excludes every rostered player and includes Free Agent Fred.
  5. **US2-5**: `player_status` rows exist with `as_of = --as-of` and `source='yahoo'`.
     `get_league` shows Butler `Q`, Iggy `IL`/`reserve`, Dybantsa `NA`/`reserve`.
  6. **US2-6**: reloading a modified `valid.csv` (Butler moved from `t.01` to `t.03`, which then has 2 active players) replaces the rosters
     atomically, and `get_league` reflects the new state.
  7. **Rejections**: `over_cap.csv`, `duplicate.csv`, `inconsistent_team.csv` and `bad_status.csv`
     each exit with 2 and write nothing, and each report lists every violation.
  8. **SC-003**: reloading the identical file gives 0 inserted and 0 updated.
- [X] T033 [P] [US2] Write `backend/tests/integration/test_core_league.py` (fixture DB):
  - `list_leagues` returns `fixture-league` with capacity 3 and format `9cat_h2h`.
  - `get_league`:
    - teams ordered by `source_team_key`, with manager names
    - roster `slot` and latest `status`, defaulting to `healthy` when there is no status row
  - `get_free_agents` returns active, unrostered players only, never Old Vet (`is_active=0`).

### Implementation for User Story 2

- [X] T034 [P] [US2] Implement `backend/src/ffmodel/adapters/roster_csv/parse.py`:
  - `RosterRow` dataclass:
    - fields: `line_no`, `team_key`, `external_id`, `name`, `positions`, `nba_team`, `status`,
      `slot`, `team_name`, `manager`
  - `parse_roster_csv(path) -> tuple[list[RosterRow], list[Problem]]`:
    - reads with `csv.DictReader` and `encoding="utf-8-sig"`
    - applies rejection rules 1, 2 and 6 from `contracts/roster-csv.md`
    - the allowed statuses are exactly `('healthy','DTD','GTD','Q','O','SUSP','IL','IL+','NA')`,
      with blank meaning healthy
    - reserve statuses are `IL`, `IL+` and `NA`
- [X] T035 [P] [US2] Implement `backend/src/ffmodel/adapters/roster_csv/match.py` with
  `match_rows(conn, rows, source) -> tuple[dict[line_no, player_id], list[Problem]]`:
  - follows the research R7 order: only `match_method='user'` rows are used directly; stored `auto`
    rows are ignored and the match is recomputed
  - the candidate pool is active players plus players with `player_game` rows in the previous
    season
  - each `Problem` for an unresolved row carries the 3 nearest candidates
    `(player_id, full_name, team)` by `difflib.SequenceMatcher` on `search_name`, plus a fix hint
    `ffm roster resolve --source <source> <external_id> <player_id>`
- [X] T036 [US2] Implement `backend/src/ffmodel/adapters/roster_csv/loader.py` with
  `load_roster(engine, path, league_key, name=None, season=None, scoring_format="9cat_h2h",
  capacity=10, source="yahoo", as_of=None) -> LoadSummary`. Steps:
  1. `start_run('roster_csv', scope)`.
  2. Parse and match.
  3. Apply rejection rule 3: duplicate player after matching.
  4. Apply rejection rule 4: the count of `slot='active'` per team must not exceed `capacity`.
  5. If there are any problems, `finish_run('rejected', report=<text table as in
     contracts/cli.md>)` and return a rejected summary without writing anything.
  6. Otherwise, in ONE transaction:
     1. upsert `fantasy_league` by `league_key`
     2. upsert `manager` by `(league_id, display_name)`
     3. upsert `fantasy_team` by `(league_id, source_team_key)`
     4. upsert `roster_entry` by `(league_id, player_id)`, and delete entries no longer present
     5. upsert `player_status(player_id, source, as_of)`
     6. upsert `player_external_id(source, external_id, match_method='auto')`, never overwriting
        `'user'`

     Then `finish_run('succeeded')`.

  The `season` default is `current_season()`, as in FR-015. If that season has no `season` row
  yet, reject with a message to run `ffm load nba` first.
- [X] T037 [US2] Add `resolve_match(engine, source, external_id, player_id)` to
  `backend/src/ffmodel/adapters/roster_csv/loader.py`. It validates that the player exists and
  upserts `player_external_id` with `match_method='user'`.
- [X] T038 [P] [US2] Implement `backend/src/ffmodel/core/data/league.py` per
  `contracts/read-api.md`, with `list_leagues`, `get_league` and `get_free_agents`:
  - `get_free_agents` selects `player WHERE is_active = 1 AND player_id NOT IN (SELECT player_id
    FROM roster_entry WHERE league_id = :id)`, ordered by `full_name`.
  - The latest status is the `player_status` row with the greatest `as_of`, with ties broken by
    `source`.
  - Export the functions from `core/data/__init__.py`.
- [X] T039 [US2] Extend `backend/src/ffmodel/cli.py` with these commands, per `contracts/cli.md`:
  - `load roster PATH`, with:
    - `--league-key` (required)
    - `--name`, `--season`, `--format` (default `9cat_h2h`)
    - `--capacity` (default 10), `--source` (default `yahoo`), `--as-of`
  - `roster resolve --source SOURCE EXTERNAL_ID PLAYER_ID`

  Exit with 2 on a rejected load and print the report.

**Checkpoint**: The US2 tests pass. `ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv
--league-key ccsv-2026 …` works after an NBA load (quickstart C).

---

## Phase 5: User Story 3 - Know who plays when, and how often players miss games (Priority: P2)

**Goal**: Core reads for games in a date range (tactical) and missed games (strategic), based on
stints (FR-021).

**Independent Test**: Against the fixture DB, counts match the hand-built schedule. Iggy Injured
has missed 4 of 10. Postponed and cancelled games are never counted.

### Tests for User Story 3

- [X] T040 [P] [US3] Write `backend/tests/integration/test_core_availability.py` (fixture DB):
  1. **Upcoming games**: `count_team_games(Iggy, 2026-10-31, 2026-11-08,
     statuses=("scheduled",))` equals 3 (S2, S4, S7). The postponed S3 and cancelled S5 are
     excluded.
  2. **Missed games**: `get_availability(Iggy, 2026-10-20, 2026-10-29)` gives `team_games=4`,
     `games_played=2`, `games_missed=2`.
  3. **Trade**: `get_availability(Tradeson, 2025-10-21, 2026-04-12)` gives `team_games=18`,
     `games_played=17`, `games_missed=1`. That is 14 DAL finals through 2026-02-09 (k = 3…55),
     plus 4 ATL finals from 2026-02-10. The miss is k = 55, the boundary game.
  4. **Rookie**: `get_availability(Dybantsa, 2026-10-20, 2026-10-29)` gives `team_games=4`,
     `games_played=3`, `games_missed=1`.
  5. **Regular season only** (FR-012): the fixture's preseason, play-in, and playoff games are never
     counted in `team_games`, `games_played`, or `count_team_games`.
  6. **Retired**: `count_team_games` for Old Vet in 2026-27 is 0, because he has no stint.

### Implementation for User Story 3

- [X] T041 [US3] Implement `backend/src/ffmodel/core/data/availability.py` per
  `contracts/read-api.md`:
  - `count_team_games(conn, player_id, start, end, *, statuses=("final","scheduled"))`
  - `get_availability(conn, player_id, start, end)`

  Every query filters `game.season_type = 'regular'` (FR-012).

  Join `game` to `player_team_stint` with:
  - `stint.team_id IN (game.home_team_id, game.away_team_id)`
  - `game.game_date BETWEEN stint.start_date AND COALESCE(stint.end_date, '9999-12-31')`

  A player's `games_played` is their `player_game` rows joined to `final` games in the range and
  regular season. Export the functions from `core/data/__init__.py`.

**Checkpoint**: The US3 tests pass, and tactical and strategic inputs are available to tools.

---

## Phase 6: User Story 4 - Compare any players across seasons (Priority: P3)

**Goal**: Player search and game history reads, including last-N across seasons with a
found/requested count (FR-020, FR-020a, FR-023, FR-024).

**Independent Test**: Against the fixture DB:
- "doncic", "Dončić" and "lu don" all find Dončić
- last 15 for Dončić returns 4 + 11
- Dybantsa's last 15 returns "3 of 15"
- Old Vet's history is still returned

### Tests for User Story 4

- [X] T042 [P] [US4] Write `backend/tests/integration/test_core_players.py` (fixture DB):
  1. `search_players("doncic")`, `("Dončić")` and `("lu don")` all return Dončić first.
  2. `search_players("marcus twin")` returns both twins.
  3. `search_players("schroder")` finds Schröder.
  4. `search_players("vet", active_only=True)` returns nothing; without `active_only` it returns
     Old Vet.
  5. `limit` is respected.
  6. `get_player` returns positions as a tuple (`("G","F")`) and the current team abbreviation, or
     None for Old Vet.
  7. `get_player` returns None for an unknown ID.
- [X] T043 [P] [US4] Write `backend/tests/integration/test_core_games.py` (fixture DB, with
  `as_of=FIXTURE_TODAY`):
  1. **US4-4**: `get_last_n_games(Dončić, 15)` returns 15 games, newest first. The first 4 are
     `2026-27` and the next 11 are 2025-26 games k = 71…61. `found=15`, `is_short=False`, and
     the preseason, play-in, and playoff games are excluded.
  2. **US4-5**: `get_last_n_games(Dybantsa, 15)` returns `found=3`, `requested=15`,
     `is_short=True`.
  3. `get_last_n_games(Dončić, 15, as_of=date(2026, 10, 19))` returns 15 games, all from
     `2025-26`.
  4. **US4-3**: `get_player_history(Old Vet)` returns 30 games, all from `2025-26`, even though he
     is inactive.
  5. `get_player_history(Dončić, seasons=["2026-27"])` returns 4 games, and
     `get_player_history(Dončić)` returns 74 games.
  6. Each `PlayerGameLine` has the right `team` and `opponent` abbreviations, and its raw
     components equal the stored row. It has no percentage attributes.

### Implementation for User Story 4

- [X] T044 [P] [US4] Implement `backend/src/ffmodel/core/data/players.py`:
  - `search_players(conn, query, *, active_only=False, limit=25)`:
    - Each word from `name_words(query)` is required: `search_name LIKE '%' || :w0 || '%' AND …`,
      with the parameters bound.
    - Order by (`search_name` starts with the first word) DESC, then `full_name`.
  - `get_player(conn, player_id)`.

  Export both from `core/data/__init__.py`.
- [X] T045 [P] [US4] Implement `backend/src/ffmodel/core/data/games.py`:
  - `get_last_n_games(conn, player_id, n, *, as_of=None)`:
    - joins `player_game` to `game` and `nba_team`
    - filters `game_date <= as_of` (default today) and `game.season_type = 'regular'` (FR-012)
    - orders by `game_date DESC, game_id DESC`, limited to `n`
  - `get_player_history(conn, player_id, *, seasons=None)` returns regular-season
    games in date order, newest first.
  - Both return `PlayerGameLine`. The opponent is the other team of the game.

  Export both from `core/data/__init__.py`.
- [X] T046 [US4] Extend `backend/src/ffmodel/cli.py` with `players search QUERY`, which calls
  `core.data.search_players` and prints `[player_id] full_name (TEAM) positions`.

**Checkpoint**: All four stories pass their tests on their own.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T047 [P] Write `backend/tests/contract/test_offline_reads.py` (SC-006):
  - Using `fixture_engine`, with network blocking asserted active, call every public function in
    `ffmodel.core.data`.
  - Assert that each returns without error and is non-empty where the fixture guarantees data.
  - **SC-007 checklist**: one assertion per Impact Analysis input, each naming the read that
    answers it:
    - last-X-game window → `get_last_n_games`
    - games in a chosen date range → `count_team_games(statuses=("scheduled",))`
    - missed games → `get_availability`
    - rosters and all league teams → `get_league`
    - free agents → `get_free_agents`
    - current status → `RosterPlayer.status`
    - player lookup → `search_players`
  - **No `nba_api` import**: run `subprocess.run([sys.executable, "-c", "import sys,
    ffmodel.core.data; assert 'nba_api' not in sys.modules"])` and assert exit code 0.
- [X] T048 [P] Write `backend/README.md`. Cover:
  - setup (`uv sync`)
  - the `ffm` commands, linking to `specs/001-league-data-schema/contracts/cli.md`
  - `FFMODEL_DB_URL`
  - the residential-network note for stats.nba.com
  - how to run offline tests, the live tests (`-m live`), and `lint-imports`
- [X] T049 Run `uv run ruff check --fix && uv run ruff format`, `uv run lint-imports`, and
  `uv run pytest` in `backend/`. Fix any findings.
- [X] T050 Run quickstart sections B and C manually, on a residential network. Load the 2026-27 and
  2025-26 seasons, then `ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv --league-key
  ccsv-2026 --name "CCSV Rumble" --season 2026-27 --capacity 10`. Then:
  - Record the auto-match rate (SC-005 requires at least 175 of 184).
  - Resolve any leftovers with `ffm roster resolve`.
  - Run `assert_contract_invariants` against the real DB.
  - Time each `ffmodel.core.data` read once against the real DB. The plan's target is under
    100 ms each.
  - Spot-check 3 teams' next-7-day game counts against the official NBA.com schedule (SC-004).
  - Note the results in `specs/001-league-data-schema/quickstart.md` under a new "Validation log"
    heading.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T002 comes before T003 and T004 (they need the project).
- **Foundational (Phase 2)**: depends on Setup and blocks all stories.
  - T005 → T006 → T007 come first.
  - Then T008–T013 and T015 can run in parallel.
  - T014 needs T007 and T008. T016 needs T012 and T014.
- **User stories (Phases 3–6)**: each depends only on Foundational.
  - US1 uses recorded responses.
  - US2, US3 and US4 use the fixture DB, not US1's loader, so all four can run in parallel.
- **Polish (Phase 7)**: depends on every story. T050 also needs a working network.

### User Story Dependencies

- **US1 (P1)**: independent; it is the only story that touches `nba_api`.
- **US2 (P1)**: independent of US1 for tests. Real-world use (quickstart C) needs US1's data
  first.
- **US3 (P2)**: independent; reads the stints that the fixture provides (US1 produces them in
  production).
- **US4 (P3)**: independent.
- **Shared file**: `cli.py` is edited by T028, T039 and T046 in that order. These edits must not
  run in parallel.

### Within Each User Story

- Tests are written first and must fail. Then pure modules ([P]), then loaders and read
  functions, then CLI wiring.

## Parallel Examples

```bash
# Phase 2 after T007:
Task: "T008 normalize_name in backend/src/ffmodel/contract/names.py"
Task: "T010 schema contract tests in backend/tests/contract/test_schema.py"
Task: "T013 upsert + load_run helpers in backend/src/ffmodel/adapters/common.py"
Task: "T015 read models in backend/src/ffmodel/core/data/models.py"

# US1 tests, together:
Task: "T019 mapping tests"  Task: "T020 stint tests"  Task: "T021 client tests"
# US1 pure modules, together:
Task: "T024 client.py"  Task: "T025 mapping.py"  Task: "T026 stints.py"

# Across stories, once Phase 2 is done:
Task: "US1 (T017–T028)"  Task: "US2 (T029–T039)"  Task: "US3 (T040–T041)"  Task: "US4 (T042–T046)"
```

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 and Phase 2: the contract exists and is tested.
2. Phase 3 (US1): real NBA data in the DB.
3. **Stop and validate**: run the US1 tests, then `ffm load nba` live.

### Incremental Delivery

1. Add US2 to get your real league loaded (quickstart C). With US1, that covers everything Impact
   Analysis needs to show rosters.
2. Add US3 to get tactical game counts and strategic injury-proneness inputs.
3. Add US4 to get last-N windows with the asterisk count, and search. **Impact Analysis needs
   `get_last_n_games` for its distribution fits, so do US4 before starting that feature, despite
   its P3 label.**
4. Polish: offline guarantee (SC-006), README, live validation.
