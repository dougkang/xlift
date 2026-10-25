# API Contract Changes: Recency-Weighted Player Projections

The request and response **shapes are unchanged**. Only a default and a meaning change. Base
contract: [002 api.md](../../002-impact-analysis/contracts/api.md).

## `POST /api/impact/analyze` and `POST /api/impact/players`

`ScenarioRequest.window`:

| | Before | After |
|---|---|---|
| default | 15 | **82** |
| range | 1–82 | 1–82 |
| meaning | games each projection uses, equally weighted | **most** games a projection may use; recent games weigh more |

Example request (window omitted takes 82):

```json
{"league_id": 1, "team_id": 1, "mode": "strategic"}
```

The response's `settings.window` echoes the value used (82 by default).

## Unchanged semantics

- Roster rows' `footnote_marker` and footnotes ("* N of X games") keep their rule: shown when a
  player has fewer games than `window`. With the new default, players with fewer than 82 games
  in the loaded history are footnoted.
- Availability-derived values (strategic games per period, availability shown anywhere) are
  identical to before for the same data and as-of date.
- Results are deterministic for the same request and seed.

Generated frontend types need no regeneration for shape. The default lives in the request model
and is echoed back.
