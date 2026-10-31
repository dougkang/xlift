# Data Model: Player Picker Filters and Category Sort

No schema change.

| Field (PlayersRequest) | Type | Rule |
|---|---|---|
| `positions` | list of `"G"`, `"F"`, `"C"` | empty = all; match any |
| `owners` | list of `"fa"` or team id | empty = all; `"fa"` = free agents |
| `sort_categories` | list of category keys | empty = total xLift; unknown key → 422 |

| Field (PlayerRow) | Type | Rule |
|---|---|---|
| `sort_xlift` | float \| null | sum of the row's per-category xLift over `sort_categories`; null when none picked or unscored |
