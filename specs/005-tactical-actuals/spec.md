# Feature Specification: Current Matchup (Tactical Week-to-Date Actuals)

**Feature Branch**: `005-tactical-actuals`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "tactical mode should include games already played in the current matchup week. alongside the roster snapshot, load a snapshot of each team's current aggregated (week-to-date) category stats for the matchup, and add the simulated remaining games on top of those actuals so chance to win, H2H, and per category difference reflect the whole matchup, not just the rest of the week."

**Refinements from discussion**:
- **Dropped players:** a player dropped mid-week must still have their collected stats credited
  to the team, and must not have any later games credited to it.
- **matchups.csv:** the current matchup state is imported from a separate `matchups.csv`,
  produced by the roster exporter (`~/dev/ccsv-rumble-page/data/matchups.csv`). It holds each
  team's week-to-date **team totals** from the fantasy platform's matchup pages.
- **Tactical is the current matchup:** tactical mode no longer lets you choose an opponent or a
  week. It always shows your team's current matchup.
- **Opponent's roster:** in tactical mode, the H2H table is replaced by the opponent's roster,
  which is read-only.
- **Dates from the files:** the as-of date of both the roster import and the matchup import is
  inferred from each file's last-modified date, unless given explicitly.

## Overview

Today, tactical mode works like this:
- you pick any opponent and any week;
- it simulates only the games left in that week;
- both teams start from zero.

So mid-week it answers "who wins the rest of the week?" rather than "who wins this matchup?".

This feature redefines tactical mode as **the current matchup**, driven by an imported
`matchups.csv`. The file has one row per team, with:
- the week number;
- the team's opponent;
- the team's week-to-date totals as the fantasy platform reports them (makes and attempts,
  3PM, PTS, REB, AST, STL, BLK, TO).

At import, the state is also given an **as-of date**: every game on or before it is in the
totals. It is also given a **matchup period**: the week's start and end dates.

Tactical results become:

> **final matchup total = the team's week-to-date total (fixed) + simulated games after the
> as-of date for players currently on the team**

**Dropped players need no special handling.** The platform's team total already includes the
games a dropped player played for the team, counting only days in an active slot. Their later
games can't count for the team, because they are no longer on its roster.

Strategic mode doesn't change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See who wins my current matchup (Priority: P1)

As a league member mid-week, I switch to tactical mode and immediately see my current matchup:
the opponent I'm actually playing this week. Chance to Win, the per-category totals and the
projected category record reflect what has already happened plus what's projected for the rest
of the week.

**Why this priority**: it is the point of the feature. The question I care about mid-week is
whether I'll win this matchup, counting the lead or deficit I already have.

**Independent Test**: Import a `matchups.csv` in which my team plays Team B and leads rebounds
by a wide margin with one day left. Switch to tactical. Confirm that:
- the opponent shown is Team B, with no opponent or week picker;
- the rebound Win % is near 100%;
- the projected You / Opp totals equal the week-to-date totals plus the projected remaining
  games.

**Acceptance Scenarios**:

1. **Given** an imported matchup state, **When** I select my team and switch to tactical,
   **Then** my opponent and the matchup period come from it. There are no opponent or week
   controls.
2. **Given** I switch to a different team, **When** tactical is shown, **Then** it shows that
   team's current matchup.
3. **Given** the current matchup, **When** results are projected, **Then** each team's total in
   every counting category equals its week-to-date total plus its simulated remaining games.
   FG% and FT% are computed from total makes ÷ total attempts.
4. **Given** the current matchup, **When** Chance to Win, the Per Category Difference table and
   the Category Breakdown are shown, **Then** all of them use the whole-matchup totals.
5. **Given** no games remain for either team, **When** tactical is shown, **Then** the results
   equal the week-to-date totals. Each category is won, lost or tied with certainty, and Chance
   to Win is 0%, 50% or 100%.
6. **Given** I make hypothetical roster moves, **When** results update, **Then** only the
   remaining games change. Week-to-date totals stay with the team that earned them.
7. **Given** my team dropped a player on Wednesday after they played Monday and Tuesday,
   **When** results are projected, **Then**:
   - their Monday and Tuesday stats count for my team, through the team total;
   - none of their later games do, because they're not on my roster.
8. **Given** that player was picked up by my opponent, **When** results are projected, **Then**
   only their games after the as-of date are simulated for my opponent. No game is counted for
   both teams.

---

### User Story 2 - Import the current matchup state (Priority: P1)

As the league's data maintainer, I import `matchups.csv` the same way I import the roster file.
The tool reports what it loaded and rejects inconsistent files.

**Why this priority**: without the data, US1 can't happen.

**Independent Test**: Import `~/dev/ccsv-rumble-page/data/matchups.csv` (week 1, 18 teams).
Confirm that:
- the import summary lists the week, the period, the as-of date and the 9 pairings;
- every league team has one row and exactly one opponent;
- importing again replaces the previous state.

**Acceptance Scenarios**:

1. **Given** a `matchups.csv`, **When** it is imported, **Then** it stores, for the league:
   - one current matchup state: the week, the period (start and end), the as-of date and the
     pairings;
   - per team: the week-to-date totals of FGM, FGA, FTM, FTA, 3PM, PTS, REB, AST, STL, BLK and
     TO.
2. **Given** an import with no as-of date given, **When** it runs, **Then** the as-of date
   defaults to the file's last-modified date (local time); a file modified before noon counts as
   the previous day. The period defaults to the Monday–Sunday week containing
   the as-of date. The summary shows both so they can be corrected with options.
3. **Given** a file naming an unknown team, a team with no row, a team listed twice, or
   pairings that aren't mutual (A plays B but B doesn't play A), **When** it is imported,
   **Then** the import fails with a clear message and nothing is stored.
4. **Given** a row whose numbers are inconsistent (makes > attempts, 3PM > FGM, or PTS ≠
   2·FGM + 3PM + FTM), **When** it is imported, **Then** the import fails and names the team.
5. **Given** a file missing a required column, **When** it is imported, **Then** the import
   fails and names the column.
6. **Given** a newer `matchups.csv`, **When** it is imported, **Then** it replaces the league's
   current matchup state.

---

### User Story 3 - Know where the matchup stands now (Priority: P2)

As a league member, I can see the current score next to the projection, so I can tell how much of
the forecast is already settled. I can also see what my opponent is fielding.

**Why this priority**: the projection is more trustworthy with the actual standing beside it, but
the tool works without it.

**Independent Test**: In tactical mode, confirm that:
- the headline shows the current category score (e.g. "Now 5–4–0") and the as-of date;
- the Per Category Difference table shows both teams' week-to-date values;
- the opponent's roster appears where H2H is in strategic mode.

**Acceptance Scenarios**:

1. **Given** the current matchup, **When** I view the tactical headline, **Then** it shows the
   opponent, the period, the current category score from the week-to-date totals, and the
   as-of date.
2. **Given** the current matchup, **When** I view the Per Category Difference table, **Then**
   each category shows both teams' week-to-date values alongside the projected final values.
3. **Given** tactical mode, **When** I look where the H2H table is in strategic mode, **Then** I
   see my opponent's roster instead:
   - it's titled with the opponent's team name;
   - it has the same columns as my roster (player, position, G), with reserve slots muted and
     status shown;
   - it has no drop buttons or other move controls, because hypothetical moves apply only to
     my team.
4. **Given** the help (feature 004), **When** I open it, **Then**:
   - the Strategic / Tactical help says tactical is always the current matchup from the
     imported file, with totals of actual-so-far plus projected remaining games;
   - the settings help no longer lists vs or Week;
   - the opponent's roster has its own help, which says it is read-only.

---

### Edge Cases

- **No matchup imported:** tactical mode is unavailable. The toggle is disabled, with the tooltip
  "This week's matchup hasn't been loaded yet". Strategic still works. User-facing text (help,
  tooltips, notices) never names data files.
- **Period over:** if the as-of date is on or after the period's end, results are final (US1
  scenario 5), and the headline marks the matchup as final.
- **As-of vs. remaining games:** games on or before the as-of date are in the totals; games after
  it are simulated. A game is never both counted and simulated.
- **Stale matchup state:** if the NBA data has completed games after the as-of date that belong
  to rostered players, those games are in neither the totals nor the simulation. A notice says
  the matchup state is older than the game data and should be re-imported.
- **NBA data older than the matchup state:** remaining games are chosen by date, after the
  as-of date, whatever their status in our game data, so a stale schedule doesn't double count.
- **Zero attempts:** FG% or FT% shows "–" as today.
- **Saved sessions:** a saved session that still holds an opponent or week from before this
  feature ignores them.
- **Roster and matchup captured on different days:** the roster file is the source of who plays
  the remaining games. If the roster's as-of date differs from the matchup's, a notice shows both
  dates so the older file can be re-captured.

## Requirements *(mandatory)*

### Functional Requirements

**Import**

- **FR-001**: The system MUST import a `matchups.csv`, separate from the roster file, with one row
  per team. Each row has:
  - week, team id and opponent id;
  - week-to-date FGM, FGA, FTM, FTA, 3PM, PTS, REB, AST, STL, BLK and TO.

  Extra columns, such as display percentages, team names or category wins, may be present and
  are not used for computation.
- **FR-002**: The import MUST take an as-of date and a period (start and end). The as-of date
  defaults to the file's last-modified date (local time), or the previous day when it was
  modified before noon (a late-night capture describes the evening before), and the period defaults to the
  Monday–Sunday week containing the as-of date. Both can be given explicitly.
- **FR-002a**: The roster import's as-of date MUST also default to the roster file's
  last-modified date rather than today. It can still be given explicitly.
- **FR-003**: The import MUST be all-or-nothing. It fails with a clear message on any of:
  unknown, missing or duplicate teams; non-mutual pairings; inconsistent numbers; missing
  columns; or malformed values.
- **FR-004**: A newer import MUST replace the league's current matchup state. Only one current
  matchup state exists per league.
- **FR-005**: The matchup state MUST live in the same shared data store as the other league
  data. The import stays separate from the engine and tools, as the roster import does.

**Tactical = current matchup**

- **FR-006**: Tactical mode MUST show the selected team's current matchup. The opponent and the
  period come from the imported state. The opponent and week controls MUST be removed.
- **FR-007**: Each team's simulated total MUST be its week-to-date total plus its simulated
  remaining games, in every simulation. Ratio categories use combined makes ÷ combined attempts.
  Week-to-date totals are never altered by the simulation's handling of invalid values.
- **FR-008**: Remaining games MUST be the NBA games after the as-of date and on or before the
  period's end, for players currently on the team.
- **FR-009**: Chance to Win, the Per Category Difference table and the Category Breakdown MUST
  use the whole-matchup totals.
- **FR-010**: Hypothetical roster moves MUST change only the remaining-games part.
- **FR-011**: When no games remain, the results MUST be determined by the week-to-date totals
  alone.
- **FR-012**: Without an imported matchup, tactical mode MUST be unavailable, with an explanation
  of why.
- **FR-013**: Strategic mode MUST be unaffected.

**Display**

- **FR-014**: The tactical headline MUST show the opponent, the period, the current category
  score and the as-of date. It is marked final once the period is over. The current score is
  computed by the server from the week-to-date totals, with ties counted explicitly.
- **FR-015**: The Per Category Difference table MUST show both teams' week-to-date values next to
  the projected finals.
- **FR-016**: In tactical mode, the H2H table MUST be replaced by the opponent's roster, titled
  with the opponent's team name. It is read-only, with no drop or move controls. Strategic mode
  keeps the H2H table.
- **FR-017**: A stale matchup state, one with completed games after its as-of date, MUST raise a
  notice.
- **FR-017a**: When the roster's as-of date differs from the matchup state's as-of date, tactical
  mode MUST show a notice with both dates.
- **FR-018**: The help (feature 004) MUST be updated:
  - the settings help drops vs and Week;
  - the Strategic / Tactical help says tactical is the current matchup, with actual plus
    projected totals;
  - the tactical headline and table help mention the current score and the week-to-date values;
  - the opponent's roster gets its own help, which says it is read-only.
- **FR-019**: The move-impact highlighting (feature 003) MUST keep working. Before and after
  share the same week-to-date totals.

### Key Entities

- **Current matchup state**: per league, the week, the period (start and end), the as-of date,
  and when it was imported. It is replaced on each import.
- **Team week-to-date line**: per team in the state, the opponent and the week-to-date totals of
  each counting stat (FGM, FGA, FTM, FTA, 3PM, PTS, REB, AST, STL, BLK, TO). Pairings are
  mutual.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In tactical mode, the opponent shown matches the imported pairing for 100% of
  teams, with no opponent or week control on the page.
- **SC-002**: For every category, the projected mean total equals the week-to-date total plus the
  mean of the simulated remaining games, within rounding.
- **SC-003**: With no games remaining, Chance to Win and every category's Win % are exactly 0%,
  50% or 100%. They match the category results of the week-to-date totals (the file's
  `cat_wins`) in 100% of categories.
- **SC-004**: Importing `~/dev/ccsv-rumble-page/data/matchups.csv` succeeds with 18 teams and 9
  mutual pairings in under 5 seconds, and leaves exactly one current matchup state.
- **SC-005**: Strategic results are identical before and after this feature for the same inputs
  and seed.
- **SC-006**: A user can read the opponent, the current category score and the as-of date from
  the headline without opening another screen.

## Assumptions

- **Where the file comes from:** `matchups.csv` is captured by the roster exporter
  (`tools/chrome_capture.py matchups --week N` in `~/dev/ccsv-rumble-page`) from the platform's
  matchup pages. It uses the same team identifiers as `rosters.csv`. Its columns are `week,
  matchup, team_id, team_name, opponent_id, fgm, fga, ftm, fta, tpm, pts, reb, ast, stl, blk, to,
  fg_pct_display, ft_pct_display, cat_wins`.
- **Platform totals:** each team's week-to-date totals come from the platform as-is. That
  includes dropped players' games for the team and only active-slot days. The tool never
  rebuilds totals from NBA game logs.
- **As-of granularity:** the as-of date is a date, taken from the file's last-modified time. A
  capture should be taken after that date's games finish; the import report shows the date so
  it can be overridden.
- **Rosters and capture together:** `rosters.csv` and `matchups.csv` are captured at about the
  same time, so the roster describes who plays the remaining games. Their modified dates let
  the tool check this.
- **Current only:** past and future weeks aren't supported in tactical mode, so there's no
  history of matchup states.
- **Remaining-games model:** remaining-games simulation is unchanged (each player plays every
  remaining game).
- **Opponent moves:** you can't make hypothetical moves for the opponent. Their remaining games
  come from their current roster as imported.
