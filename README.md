# FF-Model

Decision aids for 9-category head-to-head fantasy basketball. The first tool is **Impact
Analysis**. It simulates your team against the league (strategic mode) or against this week's
opponent (tactical mode), so you can see what a roster move does before you make it.

- Domain primer: [docs/overview.md](docs/overview.md)
- Tool description: [docs/tool1-impact-analysis.md](docs/tool1-impact-analysis.md)
- Style guide: [docs/style.md](docs/style.md)
- Project principles: [.specify/memory/constitution.md](.specify/memory/constitution.md)

## Quickstart

### 1. Prerequisites

- **[uv](https://docs.astral.sh/uv/)**: manages Python. It downloads a suitable Python itself.
- **Node 22 LTS**, for the web frontend: `brew install node@22`.
- **A home or office network** for loading NBA data. stats.nba.com blocks many cloud and
  data-center IPs.

### 2. Install

```bash
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
```

### 3. Load data

```bash
cd backend
uv run ffm load nba            # current + previous regular seasons (~10 s; rerun anytime to refresh)
uv run ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv \
    --league-key ccsv-2026 --name "CCSV Rumble" --season 2026-27 --capacity 10
```

**Daily refresh.** `scripts/daily_update.sh` does all of it in one go: it captures rosters and
matchups from Yahoo through Chrome (with the league page open), then loads NBA stats, rosters and
matchups. `--skip-capture` loads the CSVs already on disk; `--dry-run` prints the commands.

If a roster row can't be matched to an NBA player, the load stops, lists candidates, and prints
the command to fix it, for example
`uv run ffm roster resolve --source yahoo nba.p.6205 <player_id>`. Run the roster load again after
resolving.

The database lives at `data/ffmodel.sqlite`, and git ignores it. Set `FFMODEL_DB_URL` to use
another location.

### 4. Run the app

There are two ways to run it.

**Single server.** Build the frontend once, then serve the frontend and the API together:

```bash
cd frontend && npm run build && cd ..
cd backend && uv run ffm serve      # http://localhost:8000
```

**Development, with live reload.** Use two terminals:

```bash
cd backend && uv run ffm serve --reload     # API on :8000
cd frontend && npm run dev                  # UI on http://localhost:5173 (proxies /api)
```

Open the page and pick your league and team.

## Testing

```bash
cd backend
uv run pytest                 # offline suite (network blocked; fixture data)
uv run pytest -m live         # real NBA source checks
uv run pytest -m slow         # real-database timing and stability checks
uv run lint-imports           # architecture layering rules
uv run ruff check src tests

cd ../frontend
npm test                      # Vitest + Testing Library
npm run gen:api               # regenerate API types (needs `ffm serve` running)
```

## Layout

```text
backend/    Python: data contract + loaders (ffmodel.contract, ffmodel.adapters),
            modeling core (ffmodel.core), tools (ffmodel.tools), HTTP API (ffmodel.api), `ffm` CLI
frontend/   React + TypeScript + Vite; D3 radar, Observable Plot curves
docs/       Domain docs and style guide (source of truth for rules)
specs/      Spec Kit features: 001 data schema + loaders, 002 Impact Analysis
data/       Local SQLite database (git-ignored)
```

More detail: [backend/README.md](backend/README.md) covers every `ffm` command.
