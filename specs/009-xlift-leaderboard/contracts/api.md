# API Contract: xLift Leaderboard (009)

## `POST /api/player-analysis/leaderboard`

### Request: `LeaderboardRequest`

```json
{
  "league_id": 1,
  "team_id": 7,
  "window": 82,
  "as_of": null,
  "fragility": "dab_tag",
  "evaluate_for": "team",
  "pool": "free_agents",
  "top": 25,
  "min_games": 5
}
```

| Field | Type | Default | Validation (422 otherwise) |
|---|---|---|---|
| league_id | int | required | |
| team_id | int | required | |
| window | int | 82 | 1–82 |
| as_of | date \| null | today | |
| fragility | `none` \| `last15` \| `dab` \| `dab_tag` | `dab_tag` | |
| evaluate_for | `team` \| `league` | `team` | |
| pool | `free_agents` \| `all` \| team id | `free_agents` | a team id lists only that team's players (amended 2026-10-29); the evaluated team's own id lists its roster valued as in Impact Analysis; unknown team → 404 |
| top | int | 25 | 10–50, multiple of 5 |
| min_games | int | 5 | 1–15 |

There are no `moves`, `mode`, `iterations` or `seed` fields: the leaderboard always uses the league
as imported, in strategic terms (spec FR-005).

### Response 200: `Leaderboard`

```json
{
  "settings": { "mode": "strategic", "window": 82, "as_of": "2026-10-24", "fragility": "dab_tag" },
  "evaluate_for": "team",
  "team_id": 7,
  "team_name": "Splash Bros",
  "categories": [
    { "key": "fg_pct", "label": "FG%", "higher_is_better": true },
    { "key": "to", "label": "TO", "higher_is_better": false }
  ],
  "total": 212,
  "entries": [
    {
      "player_id": 1630,
      "name": "A. Player",
      "nba_team": "SAC",
      "owner_team_id": null,
      "owner_label": "Free agent",
      "status": "",
      "games_found": 82,
      "games_requested": 82,
      "footnote": null,
      "xlift": 1.84,
      "by_category": [0.31, -0.12]
    }
  ],
  "warnings": []
}
```

- `categories` is in the scoring format's order. Each `by_category` has one value per category,
  in that order.
- `xlift` = the sum of `by_category` (spec SC-002). Values aren't rounded; the frontend shows two
  decimals.
- `entries` are in display order: `xlift` descending, then name, then `player_id`. There are at
  most `top` of them. `total` is the number of eligible players before `top`.
- Under `team`, `xlift` equals `/api/impact/players`' `xlift` for the same player, league, team,
  window, fragility and `as_of`, in strategic mode with no moves (SC-001).
- `team_name` is the selected team's name. It's included under `league` too, though League values
  don't depend on it.

### Errors

- 404: unknown league, or a team not in the league (same messages as `/api/impact/*`).
- 422: validation (FastAPI's standard body).
- A league with an unsupported scoring format returns 200 with empty `categories` and `entries`
  and `total` = 0, and a `warnings` entry `UNSUPPORTED_FORMAT`. (The response has `warnings:
  WarningModel[]`, empty otherwise.)

## Unchanged

`/api/impact/analyze` and `/api/impact/players` keep their contracts and numbers (SC-007).
