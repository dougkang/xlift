# Quickstart: Focus on an H2H Opponent

## Tests

```bash
cd backend && uv run pytest -q && uv run lint-imports && uv run ruff check .
cd frontend && npx tsc -b && npm test
```

Key checks:
- focused response: 2 radar series, `league_average` = opponent averages, `win_rate` = matchup
  chances equal to the H2H row's odds, opponent curve in place of the league's (SC-001, SC-002);
- every number about the selected team (header, H2H, rosters, xLift, own averages, ranks) is
  identical with and without focus (SC-005);
- unfocused results identical to before (pre-010 regression still passes);
- a focus change with a warm cache doesn't re-simulate (SC-003);
- frontend: clicking a row focuses, clicking again clears, mode/team/league change clears.

## See it

`ffm serve` and `npm run dev`, Strategic mode: click an H2H row. The radar shows two teams, the
League column becomes the opponent's name and averages, Win % is your chance against them, and
each breakdown chart shows the opponent's distribution. Click the row again to return.
