# Data Model: Current Matchup

## Schema (migration `0002_matchup_state.sql`)

```sql
CREATE TABLE matchup_state (
    league_id    INTEGER PRIMARY KEY REFERENCES fantasy_league (league_id),  -- one current state per league
    week         INTEGER NOT NULL CHECK (week >= 0),
    period_start TEXT    NOT NULL,
    period_end   TEXT    NOT NULL CHECK (period_end >= period_start),
    as_of        TEXT    NOT NULL,      -- games on or before this date are in the totals
    run_id       INTEGER NOT NULL REFERENCES load_run (run_id)
);

CREATE TABLE matchup_team (
    league_id        INTEGER NOT NULL REFERENCES matchup_state (league_id),
    fantasy_team_id  INTEGER NOT NULL REFERENCES fantasy_team (fantasy_team_id),
    opponent_team_id INTEGER NOT NULL REFERENCES fantasy_team (fantasy_team_id),
    fgm  INTEGER NOT NULL CHECK (fgm >= 0),
    fga  INTEGER NOT NULL CHECK (fga >= fgm),
    fg3m INTEGER NOT NULL CHECK (fg3m >= 0 AND fg3m <= fgm),
    ftm  INTEGER NOT NULL CHECK (ftm >= 0),
    fta  INTEGER NOT NULL CHECK (fta >= ftm),
    reb  INTEGER NOT NULL CHECK (reb >= 0),
    ast  INTEGER NOT NULL CHECK (ast >= 0),
    stl  INTEGER NOT NULL CHECK (stl >= 0),
    blk  INTEGER NOT NULL CHECK (blk >= 0),
    tov  INTEGER NOT NULL CHECK (tov >= 0),
    pts  INTEGER NOT NULL CHECK (pts = 2 * fgm + fg3m + ftm),   -- cross-check only
    PRIMARY KEY (league_id, fantasy_team_id),
    CHECK (opponent_team_id <> fantasy_team_id)
);
```

Notes:
- **Column names** follow `player_game`'s. The stat columns are the contract's fixed vocabulary
  (research R5).
- **Replacing a state:** a re-import deletes the league's `matchup_team` and `matchup_state`
  rows and inserts the new ones, in one transaction.
- **Roster as-of:** stays in `player_status.as_of` and `DataFreshness.roster_as_of`. Only its
  default changes, to the file's modified date.

## Core read model (`ffmodel.core.data`)

| Type | Fields |
|---|---|
| `MatchupState` | `league_id`, `week`, `period_start: date`, `period_end: date`, `as_of: date`, `loaded_at`, `lines: dict[team_id, MatchupLine]` |
| `MatchupLine` | `team_id`, `opponent_id`, `totals: dict[str, int]` (`fgm, fga, fg3m, ftm, fta, reb, ast, stl, blk, tov, pts`) |

- **Reading it:** `get_matchup_state(conn, league_id) -> MatchupState | None`.
- **Derived helpers in core (scoring-aware):**
  - `base_vector(line, fmt) -> np.ndarray` in `fmt.base_stats` order. It raises
    `MissingStats` if any base stat isn't in the vocabulary.
  - `current_record(line_a, line_b, fmt) -> (wins, losses, ties)`, using `fmt.compare` on the
    category values of the base totals.

## Engine change

`simulate_team(..., base: np.ndarray | None = None)`. With `base`, the steps are (research R3):
1. Clip and round the remainder.
2. Apply subset constraints to the remainder.
3. Add `base`.
4. Compute derived stats.

Without `base`, the behavior is identical to today (SC-005).

## Settings

- **`AnalysisSettings`:** loses `opponent_id`, `period_start` and `period_end` as inputs. For
  tactical, `normalize` fills `opponent_id`, `period` and `matchup_as_of` from the matchup state,
  so they are derived rather than chosen.
- **Remaining-games window:** `(matchup_as_of + 1 day, period_end)`. It is empty when
  `matchup_as_of ≥ period_end`, which makes the result final.

## Frontend state (`ffm.impact.v1`)

- **Removed:** `opponentId`, `periodStart` and `periodEnd`, along with the `setOpponent` and
  `setPeriod` actions. A saved session that still has them loads and ignores them.
- **Unchanged:** `mode`, `window`, `leagueId`, `teamId`, `radarScale` and `moves`.
