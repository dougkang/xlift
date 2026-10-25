# API Contract Changes: League Shape Charts

Base: [002 api.md](../../002-impact-analysis/contracts/api.md). Additive only.

## `POST /api/impact/analyze` response

- `league_shape`: `CategoryShape[] | null`
  - strategic mode: one entry per category, in `categories` order;
  - `null` in tactical mode, for an unsupported scoring format, or when nothing was simulated.

```json
"league_shape": [
  {
    "category": "pts",
    "teams": [
      {"team_id": 7, "team_name": "…", "place": 1, "rank": 1, "value": 412.3, "selected": false},
      {"team_id": 1, "team_name": "…", "place": 2, "rank": 2, "value": 405.9, "selected": true}
    ],
    "gaps": [
      {"to_place": 1, "gap": 6.4, "null_gap": 9.8, "mark": "climb"},
      {"to_place": 2, "gap": 1.1, "null_gap": 5.2, "mark": "cushion"}
    ],
    "before": {"place": 4, "rank": 4, "value": 398.0}
  }
]
```

Field definitions: [data-model.md](../data-model.md). Values and gaps are in the category's
units: ratios as fractions (0.473), counts as projected per-period totals.

No request changes. Every other field is unchanged.
