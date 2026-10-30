# Quickstart: H2H Each-Category Scoring

## Tests

```bash
cd backend && uv run pytest -q && uv run lint-imports
cd frontend && npm test && npx tsc -b
```

Key checks:
- the conformance suite runs for both `9cat_h2h` and `9cat_h2h_each`;
- `pre010_impact.json` comparison: most-categories results unchanged (SC-004);
- strategic win % equals the mean radar Win % (SC-001); per-opponent W+L+T = 9 (SC-002);
- a move's expected-wins change appears at one decimal (SC-003);
- H2H Total equals the headline (SC-005).

## Switch the real league

Once, from the repo root (the same roster load the daily refresh runs, plus `--format`):

```bash
(cd backend && uv run ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv \
  --league-key ccsv-2026 --format 9cat_h2h_each)
sqlite3 data/ffmodel.sqlite "select league_key, scoring_format_id from fantasy_league"
```

Later loads, including `scripts/daily_update.sh`, name no format and keep it.

## See it

`ffm serve`, open Impact Analysis: Strategic shows **Category Record** with a win %, the H2H table
shows Record and Win % per opponent; Tactical shows **Projected Record**.
