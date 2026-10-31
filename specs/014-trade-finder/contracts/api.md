# API contract: `POST /api/player-analysis/trades`

```text
Request:  { league_id, team_id, window = 82, as_of?, fragility = "dab_tag" }
Response: {
  settings: { mode: "strategic", window, as_of, fragility },
  team_id, team_name,
  categories: [{ key, label, higher_is_better }],
  rows: [{
    team_id, team_name, manager,
    trade: null | {
      give: { player_id, name, nba_team, status },
      get:  { player_id, name, nba_team, status },
      your_gain: float, their_gain: float,          # both > 0
      your_categories: [{ category: key, gain: float }]
    }
  }],
  warnings: [{ code, message }]
}
```
Unknown league or team → 404. Rows: by min(your_gain, their_gain) desc, then no-trade rows by name.
