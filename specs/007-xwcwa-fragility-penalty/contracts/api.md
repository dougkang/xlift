# API Contract Changes: xLift and the Fragility Penalty

Base contracts: [002 api.md](../../002-impact-analysis/contracts/api.md) and
[006 api.md](../../006-recency-weighted-projections/contracts/api.md). The changes are additive.

## Request: `ScenarioRequest` (analyze and players)

| Field | Type | Default | Meaning |
|---|---|---|---|
| fragility | `"none" \| "last15" \| "dab" \| "dab_tag"` | `"dab_tag"` | how availability is estimated for the whole analysis |

An unknown value is rejected with 422.

## `POST /api/impact/analyze` response

- `settings.fragility`: echoes the option used.
- `rosters[].players[].xlift`: `number | null`. That player's expected weekly category wins
  added, **for the row's own team**, relative to that team's weakest active player (who gets
  `0`). Reserve players are scored as if active (their `slot` is `"reserve"`). It's `null` when
  the player has no projection.
- Strategic results with `fragility: "last15"` are identical to pre-feature results for the
  same request.

## `POST /api/impact/players` response

- `players[].xlift`: `number | null`, **for the request's selected team** (`team_id`), as a swap
  for its weakest active player.
- **Order**: free agents first, then rostered players. Within each group: `xlift` descending,
  then `name` ascending; `null` last. `offset` and `limit` page this order, so it holds across
  pages and with `query` and `free_agents_only`.

## Example

```json
{"league_id": 1, "team_id": 1, "mode": "strategic", "fragility": "dab"}
```

```json
"players": [
  {"player_id": 512, "name": "…", "owner_label": "FA", "xlift": 1.84, "…": "…"},
  {"player_id": 377, "name": "…", "owner_label": "FA", "xlift": 1.21, "…": "…"}
]
```
