# Quickstart: Player Picker Filters and Category Sort

```bash
cd backend && uv run pytest -q && uv run lint-imports && uv run ruff check .
cd frontend && npx tsc -b && npm test
```

Check: Position C lists only centers; Team (two teams) lists only their players; Sort by REB+BLK
orders by that sum, equal to Player Analysis's REB + BLK for the same player; nothing picked =
today's picker.
