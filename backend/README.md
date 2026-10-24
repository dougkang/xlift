# ffmodel backend

The shared data contract (SQLite schema) and its loaders
([`specs/001-league-data-schema/`](../specs/001-league-data-schema/)), the modeling core, the Impact
Analysis tool, and its HTTP API
([`specs/002-impact-analysis/`](../specs/002-impact-analysis/)).

```text
src/ffmodel/
  contract/   schema, migrations, connection, name normalization   (imports nothing else)
  adapters/   nba_stats, roster_csv loaders                         (write only)
  core/       data (reads), scoring, model, sim, scenario           (DB-free math except data)
  tools/      impact_analysis                                       (orchestration)
  api/        FastAPI app                                           (thin routes)
  cli.py      `ffm`
```

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
uv run ffm serve [--port 8000] [--reload]     # API (+ built frontend, if present)
```

- **Network:** stats.nba.com blocks many cloud and data-center IPs. Run `ffm load nba` from a home
  or office network.
- **Regular season only (FR-012):** postseason, preseason and All-Star games are never loaded or
  counted.

## API

`ffm serve` exposes the following; the full shapes are in
[contracts/api.md](../specs/002-impact-analysis/contracts/api.md), and live docs are at
`http://localhost:8000/docs`.

- `GET /api/health`
- `GET /api/leagues`, `GET /api/leagues/{id}`
- `POST /api/impact/analyze`: settings + moves → full analysis (strategic or tactical)
- `POST /api/impact/players`: the player picker with move eligibility

Requests are stateless. Hypothetical moves travel in every request and never touch the database.
The default simulation is 25,000 iterations with a fixed seed.

## Tests

```bash
uv run pytest            # offline: fixture DB + recorded nba_api responses, network blocked
uv run pytest -m live    # 001 real-source checks (load speed, totals, schedule)
uv run pytest -m slow    # 002 real-league checks: <2 s per analysis, seed stability ≤3 points
uv run lint-imports      # layering: contract ← adapters / core ← tools ← api
uv run ruff check src tests
```

To refresh the recorded `nba_api` responses, run
`uv run python -m tests.fixtures.nba_api.record` (needs network).
