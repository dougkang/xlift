# Research: Player Picker Filters and Category Sort

## R1. Where filtering and ranking happen
**Decision**: in `list_players` (backend), as new query fields; the page sends them.
**Rationale**: FR-008 and the constitution: the frontend renders, the tool decides. Paging is
already server-side, so filters must be too, or pages would be wrong.

## R2. Request shape
**Decision**: three list fields on `PlayersRequest`, empty meaning "no filter":
`positions: list["G" | "F" | "C"]`, `owners: list["fa" | int]`, `sort_categories: list[str]`
(category keys; unknown keys → 422 at the tool, since the format decides the keys).
**Alternatives**: comma strings (worse validation); one `filters` object (no gain).

## R3. Category values
**Decision**: when `sort_categories` is non-empty, score the candidates with
`core.value.score_pool_by_category` (the 009 breakdown) and rank by the sum over the picked
categories; each row gets `sort_xlift`. The total xLift keeps coming from `score_pool`, so with no
sort the output is byte-identical (SC-004; the pre-009/pre-010 snapshots pin the picker).
**Rationale**: one shared breakdown (FR-007); summing the breakdown can differ from `score_pool`
in the last float bit, so it isn't used for the total.

## R4. Positions
**Decision**: match if any of the player's positions is picked; values G/F/C as stored.

## R5. Owners
**Decision**: `"fa"` matches free agents; a team id matches that owner in the scenario (moves
applied). The selected team is never listed (unchanged), so it isn't offered.

## R6. Frontend controls
**Decision**: in the picker, under the search: **Position** and **Sort by** as toggle pills
(multi), **Team** as a compact multi-select (a quiet button summarizing the choice, opening a
checkbox list). Choices live in the picker's component state, reset on league change; a team that
is no longer offered is dropped. The xLift column shows the total; with categories picked, a second
column `xLift REB+BLK` shows the sum and is the sorted column.
