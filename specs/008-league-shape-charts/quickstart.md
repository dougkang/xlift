# Quickstart: Validating the League Shape Charts

## 1. Tests and gates

```bash
cd backend
uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run lint-imports
cd ../frontend && npm test && npm run build
```

Expected: everything passes, including:
- the core unit tests: places, ties, direction, missing values, gaps, null gaps, and parity
  with the rankings report's formula (SC-003);
- the integration tests: present in strategic mode, null in tactical, marks, the before marker
  with moves, and places matching the table's ranks (SC-001, SC-002, SC-004, SC-006);
- the frontend tests: both charts per category, the selected marks, strategic only.

## 2. Timing (SC-005)

On the real league, time a cold strategic analysis before and after the change (the 007
quickstart's timing snippet). Expected: within 5%.

## 3. In the app

`ffm serve --reload`, open a team in strategic mode:
- each category's block shows *League shape* and *Against null* under its distribution;
- your dot is navy, at your rank in the Per Category Ranking table;
- in Against null, the navy bar is your gap to climb a place and the light-blue bar your
  cushion; the dotted line is the normal-league gap;
- make a move: the charts update and a hollow gray circle marks your old place;
- switch to tactical: the breakdown shows no league-shape charts.
