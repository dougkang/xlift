# API contract: `POST /api/impact/analyze`

## Request

```text
ScenarioRequest
  focus_opponent_id: int | null = null      NEW  strategic only; ignored in tactical
```

- Unknown team → 404. The selected team itself → 422.

## Response

```text
AnalysisResult
  focus: { opponent_id: int, opponent_name: str } | null      NEW
SettingsEcho
  focus_opponent_id: int | null                               NEW
```

Under focus (see research R3 for the full table):

- `radar.series`: two entries, the opponent (`emphasis: "opponent"`) then the selected team;
  `win_rate` is the matchup chance (selected P(win)+½P(tie); opponent 1 − that); `ranks`,
  `normalized`, `area` unchanged. `radar.league`: `[]`.
- `category_table.rows[].league_average`: the opponent's projected average.
  `category_table.rows[].win_rate`: the selected team's matchup chance.
- `curves[].series`: role `opponent` (label: the opponent's name) replaces `league_average`;
  `leader` / `next_best` kept unless it is the opponent's team.
- Everything else unchanged.

## Changes under focus

- `changes.radar.original` / `tones`: include the opponent when its active players changed.
- `changes.category_table[c].league_average`: better when the opponent's average gets *worse*
  for the selected team (inverse of the category's direction).
- `changes.category_table[c].win_rate`: change in the matchup chance, whole points.
