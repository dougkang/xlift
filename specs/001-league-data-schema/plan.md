# Implementation Plan: League Data Schema & NBA Stats Ingestion

**Branch**: `001-league-data-schema` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-league-data-schema/spec.md`

## Summary

This feature defines version 1 of the SQL data contract that every tool reads, and the first two
adapters that fill it.

- **Contract**: 15 portable tables covering the NBA side (players, teams, games, appearance-only
  box scores, team stints, schedule) and the fantasy side (league, managers, teams, rosters,
  status snapshots), plus a load audit log. It contains no scoring-format or source-specific
  structure.
- **NBA stats adapter**: fills the NBA side from four bulk `nba_api` endpoints (about 4 requests
  per season), with incremental, idempotent upserts.
- **Roster CSV adapter**: loads a Yahoo-style roster export with accent-, suffix-, and
  initial-tolerant name matching, and remembers user resolutions.
- **Read interface** (`ffmodel.core.data`): gives tools last-N-games (crossing seasons, with a
  found/requested count), team games and missed games, league snapshots, free agents, and search.

## Technical Context

**Language/Version**: Python 3.12 (via `uv`; `requires-python >=3.12`)

**Primary Dependencies**: `nba_api` 1.11.x (adapter only), SQLAlchemy 2.x Core, `anyascii`, Typer;
dev: pytest, import-linter, ruff

**Storage**: SQLite (constitution) through SQLAlchemy URL `FFMODEL_DB_URL`; plain-SQL migrations

**Testing**: pytest. Offline by default (fixtures and recorded `nba_api` responses); a `live`
marker for real-source checks

**Target Platform**: Local macOS/Linux workstation on a residential network (stats.nba.com blocks
many cloud IPs)

**Project Type**: Backend library + CLI (first slice of the planned `backend/` web application;
no API or frontend in this feature)

**Performance Goals**: Full load of 2 seasons in under 5 min (SC-001 allows 30); incremental
refresh in under 1 min; any core read in under 100 ms on about 55k box score rows

**Constraints**: Portable DDL (Principle VI); idempotent loads (SC-003); no partial games
(FR-008); at least 1 s between source requests

**Scale/Scope**: About 2,460 games and about 53k box score rows per 2 seasons (26,651 in 2025-26); about 550
players; 1 league × 18 teams × about 10 players

## Constitution Check

*GATE: checked before Phase 0 and re-checked after Phase 1.*

| Principle | Status | How this plan complies |
|---|---|---|
| I. Statistically Faithful Aggregation | ✅ | Only raw makes and attempts are stored; there are no percentage columns (FR-002). Aggregation stays in later core/format work. |
| II. Pluggable Scoring Formats | ✅ | The league holds `scoring_format_id` only; no category columns. Box scores carry every component any common format needs. |
| III. Distribution-Based Modeling | ✅ (enabling) | `get_last_n_games` gives a user-chosen window with season tags and a found/requested count, ready for fits and future decayed weighting. |
| IV. Tactical vs. Strategic | ✅ (enabling) | `count_team_games` (scheduled) feeds tactical game counts; `get_availability` (missed games) feeds strategic injury-proneness. |
| V. Visualization | N/A | No UI in this feature. |
| VI. Data Source Orthogonality | ✅ | Adapters only write; core only reads via SQL; import-linter enforces `core ↛ adapters` and `adapters ↛ core`. Source IDs live only in `*_external_id`. A fixture loads through the same contract (SC-006). Migrations are versioned SQL. One justified portability note is in Complexity Tracking. |
| VII. Modular Core | ✅ | Layering: `adapters → contract (schema, migrations, connection, name normalization) ← core.data`. Rosters are written only by loaders; tools get immutable snapshots. |
| Tech stack | ✅ | Python, SQLite. FastAPI and React are not touched yet. |
| Quality gates | ✅ | Schema contract tests and fixture-based core tests are planned. The statistical-core gates (aggregation, ties, seeds) do not apply because there is no engine code yet. |

**Post-design re-check (after data-model.md and contracts)**: still passing.

- **Shared normalization**: name normalization is needed by both an adapter (matching) and core
  (search). It lives in `ffmodel.contract`, which both may import and which imports neither, so
  no layering rule is broken.
- **Stints**: stint derivation is adapter logic, but its output (`player_team_stint`) is a
  source-neutral table. Core never re-derives source heuristics.

## Project Structure

### Documentation (this feature)

```text
specs/001-league-data-schema/
├── plan.md
├── research.md          # R1–R9: endpoints, season types, stints, idempotency, pacing, DB access, names, roster rules, tooling
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── schema.sql       # contract v1 DDL (validated against SQLite 3.51)
│   ├── read-api.md      # ffmodel.core.data
│   ├── cli.md           # ffm commands
│   └── roster-csv.md    # roster input format
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                 # uv project, `ffm` entry point, import-linter contracts, pytest markers
├── src/ffmodel/
│   ├── contract/                  # the schema layer: imported by adapters AND core, imports neither
│   │   ├── db.py                  # engine/connection from FFMODEL_DB_URL, SQLite pragmas
│   │   ├── migrate.py             # applies migrations/NNNN_*.sql, tracks schema_migrations
│   │   ├── migrations/0001_initial.sql
│   │   └── names.py               # normalize_name()
│   ├── adapters/
│   │   ├── loadrun.py             # load_run bookkeeping shared by adapters
│   │   ├── nba_stats/             # client.py (pacing/retry), mapping.py, stints.py, loader.py
│   │   └── roster_csv/            # parse.py, match.py, loader.py
│   ├── core/
│   │   └── data/                  # models.py (dataclasses), players.py, games.py, availability.py, league.py
│   └── cli.py                     # Typer app; wires commands to adapters/core
└── tests/
    ├── contract/                  # DDL constraints, migrations, layering
    ├── unit/                      # names, status mapping, stint derivation, matching
    ├── integration/               # fixture DB + core reads; adapters replaying recorded responses; live/
    └── fixtures/                  # fixture dataset, recorded nba_api JSON, synthetic roster CSVs
data/                              # local SQLite DB (git-ignored)
```

**Structure Decision**: Use a `backend/` root now so the later FastAPI app (`ffmodel/api/`) and a
sibling `frontend/` can be added without moving anything. No frontend scaffold is created in this
feature. `cli.py` is the only module that may import both adapters and core. It is an entry point,
not a layer, and import-linter excludes it.

## Complexity Tracking

| Deviation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `INSERT … ON CONFLICT … DO UPDATE` (not ISO SQL) in adapter write paths | Idempotent, no-op-on-identical upserts (FR-007, SC-003) | `MERGE` is ISO but unsupported by SQLite. Delete-and-reinsert breaks "zero rows changed" and opens a missing-data window. The syntax is identical in SQLite and PostgreSQL and appears only in adapters, never in DDL or core reads. |
| `player_team_stint` table, beyond the spec's entity list | Missed games and future-game counts need "which team was the player on, on date D", but the source has no DNP rows (research R3) | Inferring the team at read time puts source heuristics in core and fails for players with no appearances on their current team. |
