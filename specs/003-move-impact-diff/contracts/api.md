# Contract: `changes` in `POST /api/impact/analyze`

This extends [002 contracts/api.md](../../002-impact-analysis/contracts/api.md). There are no new
endpoints. `AnalysisResult` gains `changes`, which is `null` when `moves` is empty. `curves[].series[].role`
gains `selected_original`, present only when `changes` is non-null.

```json
"changes": {
  "header": {
    "wins":   {"delta": 2,  "tone": "better"},
    "losses": {"delta": -1, "tone": "better"},
    "ties":   {"delta": -1, "tone": "neutral"},
    "chance_to_win": null
  },
  "radar": {
    "original": [{"team_id": 1, "emphasis": "selected",
                  "ranks": [18, 17, 12, 7, 12, 17, 15, 7, 2],
                  "normalized": [0.0, 0.1, "…"], "win_rate": [0.05, 0.12, "…"]}],
    "tones": {"1": {"rank": [null, "better", null, "worse", "…"],
                    "average": ["…"], "win_rate": ["…"]}},
    "area": {"rank": {"delta": 4, "tone": "better"}, "average": {"delta": 3, "tone": "better"},
             "win_rate": {"delta": 2, "tone": "better"}}
  },
  "category_table": {
    "pts": {"rank": {"delta": -2, "tone": "better"}, "average": {"delta": 18.0, "tone": "better"},
            "league_average": null, "leader_average": null,
            "win_rate": {"delta": 6, "tone": "better"}},
    "tov": {"rank": {"delta": 1, "tone": "worse"}, "average": {"delta": 0.8, "tone": "worse"},
            "league_average": null, "leader_average": null,
            "win_rate": {"delta": -3, "tone": "worse"}}
  },
  "curves": {"pts": {"means": {"selected": {"delta": 18.0, "tone": "better"}}}},
  "matchups": {
    "2": {"category_record": {"wins": {"delta": 1, "tone": "better"},
                              "losses": {"delta": -1, "tone": "better"}, "ties": null},
          "win": {"delta": 12, "tone": "better"},
          "original_result": "loss", "transition": "flip_better"}
  },
  "matchup_totals": {"matchups": {"wins": {"delta": 2, "tone": "better"},
                                  "losses": {"delta": -1, "tone": "better"},
                                  "ties": {"delta": -1, "tone": "neutral"}},
                     "categories": {"wins": {"delta": 5, "tone": "better"},
                                    "losses": {"delta": -4, "tone": "better"},
                                    "ties": {"delta": -1, "tone": "neutral"}}}
}
```

**Rules:**

- **Every `{delta, tone}` is a Change** (data-model.md). A `null` Change means "show nothing".
- **Units:** percentage values (`win_rate`, `win`, `chance_to_win`) use whole percentage points.
  `area` uses the 0–100 score.
- **Tactical mode:**
  - `header.chance_to_win` is set, and `wins`, `losses` and `ties` are null.
  - The `category_table` keys are `selected_average`, `opponent_average`, `difference` and
    `win_probability`. `opponent_average` uses the opposite tone, because the opponent getting
    worse is better for you.
  - `radar.original` and `radar.tones` include the opponent only if the opponent's active roster
    changed.
- **Keys:** `matchups` and `radar.tones` are keyed by team ID as a string (JSON object keys).
- **`OPPONENT_REQUIRED`:** `changes` is `null` when this warning is present.
