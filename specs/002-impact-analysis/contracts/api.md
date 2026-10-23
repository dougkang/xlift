# Contract: Impact Analysis HTTP API (`ffmodel.api`)

FastAPI serves JSON under `/api`. The Pydantic models in `ffmodel/api/schemas.py` are the source
of truth. The frontend types are generated from `/openapi.json`
(`npm run gen:api` → `frontend/src/api/schema.d.ts`). The shapes below are illustrative.

Every analysis request is **stateless**: it carries the settings and the full move list. The server
rebuilds the scenario from the stored league on every call (research R7).

## Shared request body: `ScenarioRequest`

```json
{
  "league_id": 1,
  "team_id": 3,
  "mode": "strategic",
  "window": 15,
  "as_of": "2026-10-23",
  "opponent_id": null,
  "period_start": null,
  "period_end": null,
  "iterations": 10000,
  "seed": 20261023,
  "moves": [
    {"type": "drop", "player_id": 412},
    {"type": "add", "player_id": 77},
    {"type": "swap", "acquire_id": 305, "give_id": 129}
  ]
}
```

- `as_of`, the period, `iterations` and `seed` are optional. The defaults are in data-model.md
  (AnalysisSettings).
- `opponent_id` matters only in tactical mode.
- The move types are `drop`, `add` and `swap`. A swap's `give_id` may be a roster player of
  `team_id` or a free agent.

## Endpoints

### `GET /api/leagues` → `LeagueSummary[]`

```json
[{"league_id": 1, "league_key": "ccsv-2026", "name": "CCSV Rumble", "season_id": "2026-27",
  "scoring_format_id": "9cat_h2h", "active_roster_capacity": 10, "team_count": 18}]
```

### `GET /api/leagues/{league_id}` → `LeagueDetail`

Returns the teams (`team_id`, `source_team_key`, `name`, `manager`) and `freshness`
(`nba_data_loaded_at`, `roster_as_of`). The UI uses it for the team and opponent selectors.
Returns 404 for an unknown league.

### `POST /api/impact/analyze` (`ScenarioRequest`) → `AnalysisResult`

```json
{
  "settings": {"mode": "strategic", "window": 15, "as_of": "2026-10-23", "iterations": 10000,
               "seed": 20261023, "period_start": null, "period_end": null, "opponent_id": null},
  "header": {"team_id": 3, "team_name": "Triton Aggies", "manager": "Jung",
             "record": {"wins": 11, "losses": 5, "ties": 1, "unit": "matchups"},
             "matchup_win_probability": null},
  "categories": [{"key": "pts", "label": "PTS", "decimals": 0, "higher_is_better": true}, "…"],
  "radar": {"team_count": 18,
            "series": [{"team_id": 3, "team_name": "Triton Aggies", "emphasis": "selected",
                        "ranks": [2, 5, 1, 9, 3, 4, 7, 12, 6]}, "…"]},
  "category_table": {"kind": "ranks",
                     "rows": [{"category": "pts", "rank": 2, "average": 412.3,
                               "league_average": 398.0, "leader_team_id": 9,
                               "leader_name": "California Burritos", "leader_average": 440.1},
                              "…"]},
  "curves": [{"category": "fg_pct", "x": [0.43, "…"],
              "series": [{"role": "selected", "team_id": 3, "label": "Triton Aggies",
                          "mean": 0.471, "density": ["…"]},
                         {"role": "leader", "team_id": 9, "label": "California Burritos",
                          "density": ["…"]},
                         {"role": "league_average", "team_id": null, "label": "League average",
                          "density": ["…"]}]}, "…"],
  "matchups": [{"opponent_id": 1, "opponent_name": "Keyboard Cats", "opponent_manager": "Doug Kang",
                "matchup": {"win": 0.61, "tie": 0.08, "loss": 0.31},
                "category_record": {"wins": 5, "losses": 3, "ties": 1}, "result": "win",
                "categories": {"pts": {"win": 0.55, "tie": 0.01, "loss": 0.44}, "…": {}}}, "…"],
  "matchup_totals": {"matchups": {"wins": 11, "losses": 5, "ties": 1},
                     "categories": {"wins": 80, "losses": 63, "ties": 10}},
  "rosters": [{"team_id": 3, "team_name": "Triton Aggies", "manager": "Jung",
               "open_active_slots": 0,
               "players": [{"player_id": 307, "name": "Luka Dončić", "nba_team": "LAL",
                            "positions": ["G", "F"], "slot": "active", "status": "healthy",
                            "games_found": 15, "games_requested": 15, "games_remaining": null,
                            "footnote_marker": null, "moved": false}]}, "…"],
  "footnotes": [{"marker": "*", "player_id": 588, "text": "* 0 of 15 games"}],
  "warnings": [],
  "freshness": {"nba_data_loaded_at": "2026-10-23T20:51:07+00:00", "roster_as_of": "2026-10-23"}
}
```

**Strategic mode**:
- `category_table.kind` is `"ranks"`.
- `radar.series` has every team.
- Curve roles are `selected`, `leader` (or `next_best` when the selected team is the leader), and
  `league_average`.

**Tactical mode**:
- `header.record.unit` is `"categories"`, and `matchup_win_probability` is set.
- `category_table.kind` is `"differences"`, with rows
  `{category, selected_average, opponent_average, difference, favors}`.
- `radar.series` has the selected team and the opponent only.
- Curve roles are `selected` and `opponent`.
- `matchups` has a single entry.

**Warnings**:

| Code | When | Effect |
|---|---|---|
| `OPPONENT_REQUIRED` | Tactical with no `opponent_id` | `header.record`, `radar`, `curves` and `matchups` are null or empty; rosters are still returned |
| `NO_GAMES_REMAINING` | Every games-remaining value is 0 | The result is still returned |
| `UNSUPPORTED_FORMAT` | The league's format isn't registered | Projections are empty, and the message names the format |

**Errors**:

| Status | When | Body |
|---|---|---|
| 422 | An invalid move | `{"detail": {"move_index": 2, "code": "NO_ACTIVE_SLOT", "message": "Triton Aggies has no open active slot"}}` |
| 422 | Invalid settings (FastAPI validation) | Window outside 1–82, `period_end < period_start`, or `opponent_id == team_id` |
| 404 | Unknown league, team or opponent | — |

### `POST /api/impact/players` (`ScenarioRequest` + `"query": "doncic"`, `"limit": 50`, `"offset": 0`) → `PlayerPage`

```json
{"total": 412, "players": [
  {"player_id": 77, "name": "Free Agent Fred", "nba_team": "DAL", "positions": ["C"],
   "owner_team_id": null, "owner_label": "FA", "status": "healthy",
   "games_found": 15, "games_requested": 15, "games_remaining": 3, "footnote": null,
   "eligibility": {"can_add": true, "add_blocked_reason": null,
                   "swap_give_options": []}},
  {"player_id": 305, "name": "Jalen Brunson", "nba_team": "NYK", "positions": ["G"],
   "owner_team_id": 18, "owner_label": "Woo-Tang 4eva", "status": "healthy",
   "games_found": 15, "games_requested": 15, "games_remaining": null, "footnote": null,
   "eligibility": {"can_add": false, "add_blocked_reason": "On Woo-Tang 4eva: swap required",
                   "swap_give_options": ["roster", "free_agent"]}}
]}
```

- **Which players**: every NBA player who is active or rostered and not on the selected team, after
  moves.
- **Search**: the query is accent-insensitive (001 `normalize_name`).
- **Order**: free agents first, then by name.
- **`games_remaining`** is set only in tactical mode.
- **`swap_give_options`**:
  - `"roster"` is listed when the selected team has any player (a trade needs no open slot);
  - `"free_agent"` is listed only when the selected team has an open active slot.

## Other

- `GET /api/health` returns `{"status": "ok", "schema_version": 1}`.
- Dev setup:
  - **CORS**: allowed for the Vite dev origin, `http://localhost:5173`.
  - **Production**: `ffm serve` also serves `frontend/dist` at `/`.
