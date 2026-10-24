# Phase 0 Research: Current Matchup (Tactical Week-to-Date Actuals)

## R1. Source file: team totals, not per-player rows

**Decision**: import the exporter's existing `matchups.csv`. It has one row per team with
week-to-date team totals:

```text
week, matchup, team_id, team_name, opponent_id, fgm, fga, ftm, fta, tpm, pts, reb, ast, stl, blk, to,
fg_pct_display, ft_pct_display, cat_wins
```

**Rationale**:
- The platform's team totals already credit dropped players' games correctly, counting only
  active-slot days. Later games can't count for the old team, because the player isn't on its
  roster. The dropped-player requirement therefore holds with no per-player data.
- The exporter already captures this file (`tools/chrome_capture.py matchups --week N`).

**Validated against the real file** (week 1, captured 2026-10-23 23:19):
- 18 teams, the same set as `rosters.csv`;
- 9 mutual pairings;
- `pts = 2·fgm + tpm + ftm` on every row;
- `cat_wins` matches a recomputed 9-category comparison on every row.

**Alternatives considered**: per-player rows with a rostered or dropped status. That needs
per-date roster and stat fetching, which the exporter doesn't have. It was dropped in favour of
the team totals the exporter already captures.

## R2. Dates: inferred from the files' last-modified times

**Decision**:
- **As-of date:** both the matchup import and the roster import default their as-of date to the
  file's last-modified date in local time, or the previous day when modified before noon
  (captures at 00:07 and 00:09 on Oct 24 describe Oct 23: that day's games are done and Oct 24's
  haven't started). `--as-of` overrides it.
- **Period:** the matchup period defaults to the Monday–Sunday week containing the as-of date.
  `--period-start` and `--period-end` override it.
- **Week number:** stored from the file.

**Rationale**:
- The file carries a week number but no dates.
- The NBA `game` table holds only `game_date` with no tip-off time, so a date-time as-of couldn't
  split a day anyway.
- Our game data can lag the capture. When NBA data was loaded at 14:36, the 12 games on Oct 23
  were still marked `scheduled`, but the 23:19 capture almost certainly includes them. So
  "remaining" must be chosen by **date** (after the as-of date), not by status.

**Alternatives considered**:
- **Today's date:** wrong when importing an older file.
- **Status-based remaining games:** double counts when the NBA data is older than the capture.

## R3. Where week-to-date totals enter the simulation (Constitution I and III, research 002 R2)

**Decision**: `simulate_team` in core takes an optional per-team `base` vector of integer totals,
one per base stat. The steps run in this order:
1. Sum the simulated remainder over players.
2. Clip at 0 and round the **remainder**.
3. Apply `subset_constraints` to the remainder.
4. Add `base`.
5. Compute `derived_stats`, such as `pts`.

**Rationale**:
- **No clipping bias:** clipping the combined total would let negative noise in the remainder
  eat real week-to-date totals.
- **Constraints still hold:** the subset constraints (fgm ≤ fga and so on) hold on both parts,
  so they hold on the sum.
- **Ratios stay exact:** FG% and FT% are combined makes ÷ combined attempts, because ratio
  categories are computed from the totals.
- **Mode logic stays in core** (Constitution IV).

**PTS**: the engine derives `pts` (2·FGM + 3PM + FTM). The imported `pts` is only checked at
import (R5), never used as an input.

## R4. Remaining games and moves

**Decision**: tactical projections count games for each player's NBA team with
`as_of < game_date ≤ period_end`, excluding `postponed` and `cancelled` games.
`build_projections(period=...)` gets `(as_of + 1 day, period_end)`; today the start is
`max(today, period_start)`.

The X-game window still uses `settings.as_of` (today). These are **two different as-ofs**:
- **The window as-of** (today): fits player distributions.
- **The matchup as-of:** splits week-to-date totals from remaining games.

**Moves:**
- Week-to-date totals come from the matchup state, independent of the scenario.
- Remaining games come from the scenario's roster.
- So hypothetical moves, including swaps with the opponent, change only remaining games, and
  before/after (003) share the same base (FR-010, FR-019).

## R5. Import validation (adapter, Constitution VI)

**Decision**: a new adapter, `ffmodel.adapters.matchup_csv`, all-or-nothing like `roster_csv`.

- **Required columns:** `week, team_id, opponent_id, fgm, fga, ftm, fta, tpm, pts, reb, ast, stl,
  blk, to`. Other columns are ignored.
- **Teams and pairings:** every league team appears exactly once. `opponent_id` is a league team,
  isn't the team itself, and is mutual. The week is the same on every row.
- **Numbers:** non-negative integers, with `fgm ≤ fga`, `ftm ≤ fta`, `tpm ≤ fgm`, and
  `pts = 2·fgm + tpm + ftm`.
- **Column mapping:** the adapter maps file columns to contract columns (`tpm` → `fg3m`,
  `to` → `tov`).
- **Run record:** each import is recorded in `load_run` as source `matchups_csv` and scope
  `league:<key>`.

**Which stats are required**: the adapter can't import the scoring format, because the
`adapters-independent` contract forbids it. So the schema fixes the stat columns, named after
`player_game`'s columns. Core checks at read time that the format's `base_stats` are a subset of
them, and reports `MATCHUP_STATS_MISSING` otherwise.

## R6. Cache invalidation

Each import writes a `load_run` row, and both caches in `cache.py` are keyed by the latest run id,
so a re-import invalidates them automatically. The projection cache key also gains the
remaining-games window, which replaces the user-chosen period.

## R7. API and frontend shape

**Request:**
- Tactical no longer takes `opponent_id`, `period_start` or `period_end`. They are removed from
  `ScenarioRequest`; Pydantic ignores unknown fields, so old clients don't break.
- The frontend's saved session (`ffm.impact.v1`) drops `opponentId`, `periodStart` and
  `periodEnd`, along with the `setOpponent` and `setPeriod` actions.

**`LeagueDetail`:**
- Gains `current_matchup: {week, period_start, period_end, as_of, loaded_at} | null`, so the
  Tactical toggle can be disabled before any analysis.
- `Freshness` gains `matchup_as_of`.

**`AnalysisResult` (tactical):**
- `header.matchup`: `{opponent_id, opponent_name, week, period_start, period_end, as_of, final,
  current: {wins, losses, ties}}`. `current` is computed by core from the base totals with
  `fmt.compare`, so ties are explicit (Constitution I).
- `DifferenceRow` gains `selected_actual` and `opponent_actual`, the week-to-date category
  values.
- `matchups` is empty, and `matchup_totals` is null.
- `rosters` already includes every team, so the frontend renders the opponent's roster read-only
  from it.

**Warnings:**
- **Removed:** `OPPONENT_REQUIRED`.
- **Added:**
  - `MATCHUP_NOT_LOADED`: tactical requested with no state;
  - `MATCHUP_STALE`: final games after the as-of date for rostered players;
  - `ROSTER_MATCHUP_DATES_DIFFER`: the roster and matchup as-of dates differ;
  - `MATCHUP_STATS_MISSING`.
- **Kept:** `NO_GAMES_REMAINING`, now informational, since the result is final rather than empty.

## R8. Zero variance

When no games remain, every sample equals the base. `density_curves` already handles a zero
standard deviation (fixed bandwidth, padded range). Odds are exact 0, ½ or 1, because
`fmt.compare` on identical rows gives the same outcome in every simulation. A test covers
SC-003 against the file's `cat_wins`.

## R9. Strategic regression (SC-005)

Strategic code paths don't read the matchup state. A test compares strategic results on the
existing fixture before and after loading a matchup state, and requires them to be identical.
