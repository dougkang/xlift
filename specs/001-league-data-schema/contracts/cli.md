# Contract: `ffm` Command Line

Entry point `ffm`, installed from the `backend` project (`uv run ffm …`). The database location
comes from `FFMODEL_DB_URL` (default `sqlite:///data/ffmodel.sqlite` at the repo root). Every
command exits with 0 on success, 1 on failure, and 2 on a rejected load (input problems the user
must fix). Human-readable output goes to stdout and errors to stderr. `--json` prints a
machine-readable summary instead.

## Schema

```text
ffm db migrate                 Apply pending migrations. Idempotent.
ffm db version                 Print the current schema version.
```

## NBA stats loader (`adapters.nba_stats`)

```text
ffm load nba [--season 2026-27]... [--full]
```

| Option | Default | Meaning |
|---|---|---|
| `--season` (repeatable) | current and previous season (e.g. `2026-27`, `2025-26`) | Seasons to load |
| `--full` | off | Ignore the incremental cursor and re-request whole seasons (upserts stay idempotent) |

Loads regular-season data only (FR-012). In order: teams, then players (`PlayerIndex`), schedule and games, box scores, and finally
stints, which are recomputed for the affected seasons.

Output: rows inserted and updated per table, the elapsed time, and the run ID.

## Roster file loader (`adapters.roster_csv`)

```text
ffm load roster PATH --league-key KEY [--name NAME] [--season 2026-27]
                     [--format 9cat_h2h] [--capacity 10] [--source yahoo] [--as-of YYYY-MM-DD]
```

- Creates the league if `KEY` is new, and updates its settings if given. Then it replaces the
  league's rosters atomically (FR-019).
- `--as-of` dates the status snapshot. The default is today.
- On unresolved or invalid rows it exits with 2 and writes nothing to data tables. It prints, and
  stores in `load_run.report`, a table like this:

```text
UNRESOLVED  row 23  yahoo:nba.p.6205  "N. Alexander-Walker" (ATL)
            candidates: [412] Nickeil Alexander-Walker (ATL)  |  …
            fix: ffm roster resolve --source yahoo nba.p.6205 412
OVER CAP    t.99 "Example Team": 11 active > capacity 10
DUPLICATE   nba.p.5473 on t.01 and t.07
```

```text
ffm roster resolve --source SOURCE EXTERNAL_ID PLAYER_ID
```

`PLAYER_ID` is the internal `player.player_id` shown in brackets in candidate lists, not an NBA stats
person ID.

Stores a `user` match. It wins over automatic matching on every later load (FR-016, US2
scenario 3).

## Inspection

```text
ffm runs [--limit 10]          Recent load runs: source, scope, outcome, row counts, finished_at
ffm players search QUERY       Calls core search_players (smoke test for FR-023)
```
