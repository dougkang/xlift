# Data Model: Focus on an H2H Opponent

No schema change.

## AnalysisSettings (tool, extended)

| Field | Type | Rule |
|---|---|---|
| `focus_opponent_id` | int \| null | Strategic only (null in tactical). Another team in the league. Not part of the simulation-cache key. |

## Focus (result, new)

| Field | Type |
|---|---|
| `opponent_id` | int |
| `opponent_name` | str |

Null when unfocused.

## Matchup win rate (derived)

Per category c: `you[c] = P(win) + ½·P(tie)` against the opponent over the simulations;
`them[c] = 1 − you[c]`. Same odds as the H2H row's `categories`.

## Page state (frontend)

`focusOpponentId: number | null` in the scenario state. Cleared on league, team or mode change;
not persisted.

## Caches

`cache.computed`: LRU of 8 `Computed` by (original-cache key without focus, moves).
`cache.original`: key gains `focus_opponent_id`.
