# Data Model: League Shape Charts

No schema change. These are in-memory results of one analysis, plus contract fields.

## CategoryShape (per category, strategic only)

| Field | Type | Notes |
|---|---|---|
| category | string | category key, in `categories` order |
| teams | list[ShapeTeam] | ordered by place; teams without a value are omitted |
| gaps | list[ShapeGap] | N − 1 entries; empty when fewer than 3 teams have a value |
| before | ShapePoint \| null | the selected team's pre-move position; null without moves |

## ShapeTeam

| Field | Type | Notes |
|---|---|---|
| team_id | int | |
| team_name | string | |
| place | int | 1…N, unique: by competition rank, then team id (research R2) |
| rank | int | the Per Category Ranking table's rank (ties share it) |
| value | float | projected per-period average (category units) |
| selected | bool | exactly one true when the selected team has a value |

## ShapeGap

| Field | Type | Notes |
|---|---|---|
| to_place | int | r: the gap between places r and r + 1, i.e. what the team at r + 1 must close to reach r |
| gap | float | \|v_r − v_{r+1}\| ≥ 0 |
| null_gap | float | (z_r − z_{r+1}) · σ ≥ 0 (research R3) |
| mark | "climb" \| "cushion" \| null | climb: to_place = selected place − 1; cushion: to_place = selected place |

## ShapePoint (before)

| Field | Type | Notes |
|---|---|---|
| place | int | in the original (no-move) league |
| rank | int | |
| value | float | |

## Validation

- At most one `climb` and one `cushion` per category.
- `teams[i].place == i + 1`.
- `gap`, `null_gap` ≥ 0; all gaps 0 when every value is equal (σ = 0).
