# API contract changes: `POST /api/impact/analyze`

Additive. Under the `matchup` rule every existing field is as before and the new ones are null
(`standings` is `"matchup"`).

```text
AnalysisResult
  standings: "matchup" | "category"                      NEW

Header
  record: RecordModel | null          null under "category"
  expected_record: ExpectedRecordModel | null            NEW, set under "category" (both modes)
  matchup_win_probability: float | null   still returned in tactical (page uses it under "matchup")

ExpectedRecordModel                                      NEW
  wins: float      losses: float      ties: float       (unrounded)
  win_pct: float   (W + ½T) / (W + L + T), 0..1

MatchupModel  (strategic H2H row)
  expected_record: ExpectedRecordModel | null            NEW, set under "category"
  result: "win" | "loss" | "tie" | null                  null under "category"

MatchupTotals
  matchups: RecordCounts | null                          null under "category"
  categories: RecordCounts                               unchanged
  expected: ExpectedRecordModel | null                   NEW, set under "category"

HeaderChange
  expected_wins: Change | null     NEW  1 decimal, better when higher
  win_pct: Change | null           NEW  whole points (scale 100), strategic only

MatchupChange
  expected_wins: Change | null     NEW  1 decimal
  original_result: ... | null      null under "category"
  transition: ... | null           null under "category" (no flips)

TotalsChange
  matchups: WLTChange | null       null under "category"
  expected_wins: Change | null     NEW  1 decimal
```

Under `"category"`, `HeaderChange.wins/losses/ties/chance_to_win` are null.

## CLI: `ffm load roster --format <id>`

Unknown `<id>` → exit 1, `unknown scoring format '<id>'; known: 9cat_h2h, 9cat_h2h_each`.
Omitted → the league keeps its stored format (new league: `9cat_h2h`).
