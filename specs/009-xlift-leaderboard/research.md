# Research: xLift Leaderboard (009)

Every item in the plan's Technical Context is known, so nothing needs clarifying. This file
records the design decisions.

## R1. Sharing xLift between tools without one tool importing another

**Decision**: move the shared domain logic out of `tools/impact_analysis` into core:

| From (`tools/impact_analysis/`) | To (`core/`) | What |
|---|---|---|
| `value.py` | `core/value/scenario.py` | per-period lines, team totals, weekly spread, who makes room (`out_line`), roster and pool scoring; plus the new by-category and league scoring (R2, R3) |
| `fragility.py` | `core/model/fragility.py` | applying a Fragility Penalty option; `dab_values` |
| `cache.py` (projections, dAB, spreads) | `core/cache.py` | the process caches, and `league_spread` |

The Impact Analysis modules stay as thin re-exports, so imports through the old paths keep
working. Re-exports don't carry monkeypatches, though: a test that patches a moved name through
the old path (e.g. `tools.impact_analysis.value.weekly_spread`) no longer affects code that now
lives in core. So the full suite runs right after the move, and any such patch moves to the core
path. `core/cache.dab` imports `dab_values` from `core.model.fragility`, not from the tool, so the
`core-not-tools` contract holds. The import stays lazy, because `fragility` imports the cache. `cache.original` (the no-moves analysis) is
specific to Impact Analysis and stays in its `cache.py`. That module's `clear()` also clears the
core caches. Player Analysis imports from core only, and reads the league through core
(`get_league`, `from_snapshot`, `get_player_details`), not through Impact Analysis's `state.py`.

A new import-linter `independence` contract between `ffmodel.tools.impact_analysis` and
`ffmodel.tools.player_analysis` enforces Constitution VII.

**Rationale**: Constitution VII says shared domain logic lives in core and no tool depends on
another's internals. xLift, the Fragility Penalty and the projection cache are exactly the shared
logic both tools need. With re-exports, the move changes no behavior: the same functions run.

**Alternatives considered**:
- *Player Analysis imports `tools.impact_analysis`*: the smallest change, but it violates VII
  directly.
- *A `tools/common` package*: it avoids moving the caches into core, but it adds a layer the
  constitution doesn't define, and the scoring and fragility code it would hold is domain logic,
  which belongs in core anyway.
- *Copy the code*: two copies of xLift would drift, which defeats SC-001.

## R2. The per-category breakdown

**Decision**: add `score_candidates_by_category(...) -> (candidates, categories)` to
`core/value/xlift.py`: the change in expected wins per category, summed over opponents only. Leave
`score_candidates` exactly as it is. A unit test asserts that the row sums of the new function
equal `score_candidates` within 1e-9.

**Rationale**: the categories sum to the net by construction (SC-002), and the picker's numbers
are untouched (SC-007). Players are ranked on the row sum of the breakdown, which equals the
picker's value within floating-point error, far below the two-decimal display (SC-001).

**Alternatives considered**: redefining `score_candidates` as the sum of the breakdown. The
results are identical, but it changes code the picker depends on for no gain.

## R3. League scope (Evaluate for: League)

**Decision**: for every team *t*, find *t*'s own out line (an open active slot or a projectionless
active player means an empty slot, else *t*'s weakest active player, as `out_line` does today),
and score every candidate by category for *t*. A player's own team is masked (NaN), and the league
value is the NaN-mean over the remaining teams, per category. The net is the sum of the
per-category means, which equals the mean of the per-team nets. Free agents average over all
*N* teams; rostered players over *N* − 1.

Under League, Pool **All players** includes the selected team's players (spec FR-016). Changing
the selected team doesn't change League values.

**Cost**: 18 teams × about 500 candidates × 17 opponents × 9 categories, about 1.4M normal-CDF
evaluations, vectorized per team: tens of milliseconds. The spread simulation is shared and
cached (R5).

**Rationale**: it's the notebook's *League (position-neutral)* definition with the app's out line
(R4).

## R4. Parity with the notebook (SC-003)

**Decision**: extend `analysis/xlift_parity.py` with two checks, both under **Last 15**, the only
option where the notebook's lines and spreads match the app's (007 R10):
- *Your team*: the leaderboard against the notebook's per-team `rgp` sum for the first team
  (what 007's check does, through the leaderboard instead of the picker);
- *League*: the leaderboard against `nanmean(rgp, axis=0)` summed over categories, for free
  agents.

**Known difference**: the app makes room with an *empty slot* when a team has an open active slot
or a projectionless active player. The notebook uses an empty slot only for the projectionless
case: with an open slot it still removes the weakest player. For a single team, 007 never hit
this. League scope averages over every team, so any team with an open active slot shifts the
League values away from the notebook's. The parity script reports which teams have open active
slots. If there are any, it reports the League check both over all teams and over the teams
without open slots, and the ±0.05 bound applies to the latter. The app's rule stays: it's 007's
decided behavior (spec 007 edge case, "a team with an empty active slot").

## R5. Settings and caches

**Decision**: `PlayerAnalysisSettings` (in `tools/player_analysis/settings.py`) is a frozen dataclass
with `league_id`, `team_id`, `window`, `as_of`, `fragility` and `games_per_period = 3`, and fixed
`mode = "strategic"` and `remaining = None`. These are the attributes the core cache keys read
(`core/cache.py` documents them as a Protocol). Player Analysis then shares warm caches with Impact
Analysis's strategic analysis and picker: same projections, dAB and spreads.

The response echoes `mode: "strategic"` (Constitution IV).

**Rationale**: the same settings give the same cache keys, which give the same numbers (SC-001)
and a fast first load after using Impact Analysis (SC-005).

## R6. Eligibility, filters and ordering (server side)

**Decision**: the pool mirrors the picker's:
- league player details plus rostered players;
- inactive free agents skipped;
- the selected team's players skipped under *Your team* only (R3).

Players without a projection (`games_found == 0`) have no xLift and are dropped. Then
`games_found < min_games` is dropped. Players are ordered by net xLift, descending, then by name,
then by id, and the server returns the top *n* with the total count of eligible players. The
footnote is the picker's (`* found of requested games`).

**Injury statuses** (for **dAB × tag**) MUST come from the same source as the picker's: the
league's player details merged with the rostered players' latest statuses
(`get_player_details(league) | rostered info`). A different source would change tag multipliers
and break SC-001 under the default setting.

**Rationale**: FR-009 says the frontend doesn't rank. Paging on the server matches the picker
(007 R7).

## R7. API shape

**Decision**: one endpoint, `POST /api/player-analysis/leaderboard`, with a request model and a response
model (see [contracts/api.md](contracts/api.md)). The response carries the format's category list
(key, label, higher-is-better) once, and each entry's `by_category` is a list in that order.

**Alternatives considered**: extending `/api/impact/players` with a breakdown. It would tie the new
tool to Impact Analysis's request (moves, mode) and its paging.

## R8. Navigation and shared settings (frontend)

**Decision**:
- **Routing**: hash routes (`#/` for Impact Analysis, `#/player-analysis` for Player Analysis) from a
  tiny `useRoute` hook that listens to `hashchange`. It needs no new dependency and no SPA fallback
  in `ffm serve`.
- **Shell**: a new `Shell` component owns `useScenario()` and renders the navigation and the
  current tool. `App` (Impact Analysis) takes the state and dispatch as props instead of creating
  them, and keeps its exports (`toRequest`).
- **What Player Analysis does with the shared state**: it reads league, team, window and fragility. It
  dispatches only `setLeague`, `setTeam`, `setWindow` and `setFragility`. It never sends moves and
  never changes `mode`, so a manager in tactical mode comes back to tactical.
- **Player Analysis's own settings** (`evaluateFor`, `pool`, `top`, `minGames`) are kept in their own
  session key, `ffm.player-analysis.v1`.
- **Controls**: `Controls` gains an option to hide Reset. Player Analysis shows the window, Fragility
  Penalty, league and team.
- **Moves note**: when the session has moves, Player Analysis shows a muted line: "The leaderboard uses
  rosters as they are, without your Impact Analysis moves."

## R9. The chart

**Decision**: Observable Plot, already used by the breakdown:
- `barX` with Plot's stack transform on `by_category` (`x` = value, `y` = player, `fill` =
  category). With Plot's default offset, positive values stack rightward from zero and negative
  values leftward, separately, which is what FR-011 needs. Implementation checks this with a test
  fixture that has a negative segment.
- `tickX` at the net xLift.
- `ruleX` at 0.

Players are ordered top to bottom by the server's order. Labels are set as text: the name
(bold, as in the style guide's name columns), the owner, and the signed net to two decimals with a
real minus sign. Tooltips use Plot's `title` channel.

**Colors**: the style guide's qualitative palette, in format category order (nine colors for nine
categories): `#a6cee3`, `#1f78b4`, `#b2df8a`, `#33a02c`, `#fb9a99`, `#e31a1c`, `#fdbf6f`,
`#ff7f00`, `#cab2d6` (the palette the user chose after implementation, replacing a darker set). The tick is `#111` over a 1px white halo (a wider white tick underneath),
so it reads on light and dark segments alike. The style amendment records this (FR-022).

**Size**: row height about 18px (the notebook's), so 25 rows is about 450px and 50 is about 900px.
The chart takes the page's width.

**Alternatives considered**: D3 by hand. Plot covers stacked bars and ticks, and the constitution
prefers it where it fits.

## R10. Docs and naming

**Decision**: the tool is **Player Analysis** (the user's choice), in the app and the docs. When
implemented, the feature:
- adds a stacked-bar leaderboard section to `docs/style.md`;
- describes the leaderboard in `docs/tool2-player-comparison.md`, whose title is already "Tool 2:
  Player Analysis";
- fixes Tool 2's entry in `docs/overview.md` to `[Player Analysis](tool2-player-comparison.md)`.
  It currently reads "Player Potential", linking `tool2-player-potential.md`, which doesn't
  exist.

The identifiers follow the name:
- the `tools/player_analysis` package;
- `POST /api/player-analysis/leaderboard`;
- the `#/player-analysis` route;
- the `ffm.player-analysis.v1` session key.
