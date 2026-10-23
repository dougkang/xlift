# Quickstart & Validation: League Data Schema

This guide proves the feature works end to end. Commands are in [contracts/cli.md](contracts/cli.md),
tables in [data-model.md](data-model.md), and the read interface in
[contracts/read-api.md](contracts/read-api.md).

## Prerequisites

- `uv` installed. Python 3.12 is fetched by uv; the system Python 3.9 is not used.
- For live checks only: a home or office network. stats.nba.com often blocks cloud and data-center IPs.

```bash
cd backend
uv sync
```

## A. Offline validation (no network; runs in CI)

```bash
uv run pytest                      # excludes the `live` marker by default
uv run lint-imports                # Constitution VI/VII layering contracts
```

Expected:

| Check | Proves |
|---|---|
| Schema contract tests pass: migrations apply to an empty DB, `ffm db version` = 1, all CHECK/UNIQUE rules reject bad rows | FR-001–FR-005 |
| Fixture dataset loads through the contract, and every read in read-api.md returns the expected values with sockets disabled | FR-025, SC-006 |
| Replayed `nba_api` responses load; a second replay changes 0 data rows | FR-006–FR-008, SC-003 |
| Synthetic roster file: abbreviated, accented, and suffixed names match; one unresolved row → exit 2, nothing written; after `roster resolve`, a reload succeeds | FR-014–FR-019 |
| "4 + 11 across seasons" and "3 of 15 found" scenarios | FR-020, FR-020a |
| `core` does not import `adapters`, and `adapters` does not import `core` | Constitution VI |

## B. Live validation (manual, `-m live`)

```bash
export FFMODEL_DB_URL=sqlite:///../data/ffmodel.sqlite
uv run ffm db migrate
time uv run ffm load nba                      # current and previous regular seasons
uv run ffm load nba                           # immediate rerun
uv run ffm runs --limit 2
```

Expected:

- The first load succeeds in well under 30 minutes (SC-001); about 10 requests in total.
- The rerun reports 0 inserted and 0 updated (SC-003); `runs` shows two `succeeded` rows.

```bash
uv run pytest -m live
```

Checks the following against the live source:

- 20 random players' season totals match the official season totals (SC-002).
- Scheduled games per team for the next 7 days match `ScheduleLeagueV2` (SC-004).

## C. Reference roster file (manual)

```bash
uv run ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv \
    --league-key ccsv-2026 --name "CCSV Rumble" --season 2026-27 --capacity 10
```

Expected:

- At least 175 of 184 rows match automatically (SC-005, ≥95%).
- Any rest are listed with candidates and a `ffm roster resolve …` hint, and the exit code is 2.
- After resolving them, the same command exits 0 with 18 teams. A third run prompts nothing and
  changes no roster rows.

Spot checks:

```bash
uv run ffm players search doncic              # → Luka Dončić (LAL)
uv run ffm players search "alexander walker"  # → Nickeil Alexander-Walker
```

In a Python shell, using `ffmodel.core.data`:

- `get_league(...)`: team `t.14` has 9 active and 3 reserve players (`IL`, `IL`, `NA`).
- `get_last_n_games(<AJ Dybantsa>, 15)`: `is_short` is True, and `found` is less than 15.
- `get_free_agents(...)`: does not include any of the 184 rostered players.
