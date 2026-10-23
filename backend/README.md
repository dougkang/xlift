# ffmodel backend

The shared data contract (SQLite schema), its loaders, and the core read interface. The design is
in [`specs/001-league-data-schema/`](../specs/001-league-data-schema/).

## Setup

```bash
cd backend
uv sync
```

The database location comes from `FFMODEL_DB_URL`. The default is
`sqlite:///<repo>/data/ffmodel.sqlite`, which is git-ignored.

## Commands

See [contracts/cli.md](../specs/001-league-data-schema/contracts/cli.md) for every option.

```bash
uv run ffm db migrate                         # apply schema migrations
uv run ffm load nba                           # current + previous regular seasons (incremental)
uv run ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv \
    --league-key ccsv-2026 --name "CCSV Rumble" --season 2026-27 --capacity 10
uv run ffm roster resolve --source yahoo nba.p.6205 <player_id>   # confirm an unmatched row
uv run ffm players search doncic
uv run ffm runs
```

- **Network:** stats.nba.com blocks many cloud and data-center IPs. Run `ffm load nba` from a home
  or office network.
- **Regular season only (FR-012):** postseason, preseason and All-Star games are never loaded or
  counted.

## Tests

```bash
uv run pytest            # offline: fixture DB + recorded nba_api responses, network blocked
uv run pytest -m live    # real-source checks (SC-001, SC-002, SC-004)
uv run lint-imports      # layering: core and adapters never import each other
uv run ruff check src tests
```

To refresh the recorded `nba_api` responses, run
`uv run python -m tests.fixtures.nba_api.record` (needs network).
