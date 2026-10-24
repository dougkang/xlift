# Data Model: Move Impact Highlighting

**There are no schema changes.** This feature adds an optional `changes` block to the 002
`AnalysisResult` (`null` when there are no moves). It also adds two curve roles and a cached
original analysis, held in memory only.

## Change (one displayed value)

| Field | Type | Rules |
|---|---|---|
| `delta` | number \| null | current − original, rounded to display precision (research R2). `null` when it rounds to 0, or when either side is missing |
| `tone` | `"better"` \| `"worse"` \| `"neutral"` | From the field's `better_when` rule (research R3). Ignored when `delta` is null |

## Transition (H2H result)

| Field | Type | Rules |
|---|---|---|
| `original_result` | `"win"` \| `"loss"` \| `"tie"` | The original analysis's result for this opponent |
| `transition` | `"flip_better"` \| `"flip_worse"` \| `"better"` \| `"worse"` \| null | Order L < T < W; the flips are L↔W only |

## Changes block (`AnalysisResult.changes`)

| Part | Contents | Inventory row |
|---|---|---|
| `header` | Strategic: `wins`, `losses`, `ties` (Change). Tactical: `chance_to_win` (Change, in points) | 1, 2 |
| `radar` | `original`: series (the selected team, plus the opponent in tactical mode if it changed) with `ranks`, `normalized`, `win_rate`. `tones`: `{rank, average, win_rate}` per series, each a list of per-category tone or null. `area`: `{rank, average, win_rate}` Change for the selected team | 3, 4 |
| `category_table` | Per category. Strategic: `rank`, `average`, `league_average`, `leader_average`, `win_rate`. Tactical: `selected_average`, `opponent_average`, `difference`, `win_probability`. All are Changes | 5, 6 |
| `curves` | Per category: `means`, a role → Change map for the plotted series. The original distributions themselves come as extra `curves[].series` entries with roles `selected_original` | 7 |
| `matchups` | Per opponent ID: `category_record` (`wins`, `losses`, `ties` Changes), `win` (Change, in points), and a Transition | 8 |
| `matchup_totals` | `matchups` and `categories` W/L/T Changes | 9 |

## Original-analysis cache (`tools/impact_analysis/cache.py`)

- **Key:** (db url, league, team, mode, window, as_of, period, opponent, seed, iterations, latest
  `load_run` ID).
- **Value:** the original analysis internals: per-team samples, category values, averages, ranks,
  normalized averages, win rates, and odds. That's enough to diff and to reuse samples.
- **Size:** LRU, 8 entries. Each entry is roughly 18 teams × 25,000 iterations × 11 stats as
  float64, about 40 MB, so the cache is kept small.

## Sample reuse

- **Reuse key:** a team's samples in the current analysis are reused from the original when its
  frozenset of active player IDs is unchanged. Mode, seed and iterations are equal by
  construction.
- **Reused teams are identical,** so every value describing an untouched team has a null change
  (SC-003).
