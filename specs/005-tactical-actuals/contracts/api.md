# Contract: API changes

## `GET /api/leagues/{id}` (`LeagueDetail`)

The response adds:

```jsonc
"current_matchup": {            // null when no matchups.csv has been imported
  "week": 1,
  "period_start": "2026-10-19",
  "period_end": "2026-10-25",
  "as_of": "2026-10-23",
  "loaded_at": "2026-10-24T06:20:00+00:00"
}
```

`Freshness` gains `matchup_as_of: string | null`.

## `POST /api/impact/analyze` (`ScenarioRequest`)

- **Removed:** `opponent_id`, `period_start` and `period_end`. Tactical derives them from the
  matchup state. Unknown fields are ignored, so older clients still work.

## `AnalysisResult` (tactical)

```jsonc
"header": {
  "record": { "wins": 5, "losses": 4, "ties": 0, "unit": "categories" },   // projected
  "matchup_win_probability": 0.62,
  "matchup": {
    "opponent_id": 3, "opponent_name": "Triton Aggies",
    "week": 1, "period_start": "2026-10-19", "period_end": "2026-10-25",
    "as_of": "2026-10-23", "final": false,
    "current": { "wins": 5, "losses": 4, "ties": 0 }                       // from week-to-date totals
  }
},
"category_table": { "kind": "differences", "rows": [
  { "category": "reb", "selected_actual": 74, "opponent_actual": 68,
    "selected_average": 101.3, "opponent_average": 96.0, "difference": 5.3,
    "favors": "selected", "win_probability": 0.71 }
]},
"matchups": [], "matchup_totals": null
```

**Field notes:**
- **`header.matchup`:** null in strategic mode.
- **`*_actual`:** each category's week-to-date value. Ratios are makes ÷ attempts, null when
  attempts are 0.
- **`*_average`:** now the projected **final** values (week to date plus remaining games).
- **`changes` (003):** keeps its shape. Before and after share the same week-to-date totals.

**Warnings:**

| Code | When |
|---|---|
| `MATCHUP_NOT_LOADED` | Tactical with no matchup state; no tactical results are returned |
| `MATCHUP_STALE` | Rostered players have `final` games after the as-of date |
| `ROSTER_MATCHUP_DATES_DIFFER` | The roster's and the matchup's as-of dates differ |
| `MATCHUP_STATS_MISSING` | The scoring format needs a stat the matchup state doesn't hold |
| `NO_GAMES_REMAINING` | Informational; the result is final |

`OPPONENT_REQUIRED` is removed.
