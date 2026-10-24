# Feature Specification: Current Matchup (Tactical Week-to-Date Actuals)

**Feature Branch**: `005-tactical-actuals`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "tactical mode should include games already played in the current matchup week. alongside the roster snapshot, load a snapshot of each team's current aggregated (week-to-date) category stats for the matchup, and add the simulated remaining games on top of those actuals so chance to win, H2H, and per category difference reflect the whole matchup, not just the rest of the week."

**Refinements from discussion**:
- **Dropped players:** a player dropped mid-week is missing from the roster file, so his
  collected stats must still be recorded and credited. He must also be recorded as dropped, so
  none of his remaining games count for that team.
- **matchup.csv:** the current matchup state is imported from a separate `matchup.csv`.
- **Tactical is the current matchup:** tactical mode no longer lets you choose an opponent or a
  week. It always shows your team's current matchup.
- **Opponent's roster:** in tactical mode, the H2H table is replaced by the opponent's roster,
  which is read-only.

## Overview

Today, tactical mode works like this:
- you pick any opponent and any week;
- it simulates only the games left in that week;
- both teams start from zero.

So mid-week it answers "who wins the rest of the week?" rather than "who wins this matchup?".

This feature redefines tactical mode as **the current matchup**, driven by a separate
`matchup.csv` imported alongside the roster file. The file holds the current matchup state:
1. the current matchup period (start and end dates) and when the state was captured (as-of);
2. the pairings, meaning which team plays which this period;
3. per team and player, the week-to-date stats he has earned for that team, and whether he is
   still **rostered** or was **dropped** mid-week.

Tactical results become:

> **final matchup total = sum of every player's week-to-date stats for the team, including
> dropped players (fixed) + simulated remaining games of players still on the team**

The opponent and the week come from the file; the user doesn't choose them.

**Dropped players:** a player dropped mid-week is missing from the roster file, but his games
for the team still count. His row in `matchup.csv` credits those stats to the team, and its
**dropped** status keeps his remaining games from counting for it. A player dropped by one team
and picked up by another has a row for each team, and each row holds only the games he played
for that team.

Strategic mode doesn't change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See who wins my current matchup (Priority: P1)

As a league member mid-week, I switch to tactical mode and immediately see my current matchup:
the opponent I'm actually playing this week. Chance to Win, the per-category totals and the
projected category record reflect what has already happened plus what's projected for the rest
of the week.

**Why this priority**: it is the point of the feature. The question I care about mid-week is
whether I'll win this matchup, counting the lead or deficit I already have.

**Independent Test**: Import a `matchup.csv` in which my team plays Team B and leads rebounds by
a wide margin with one day left. Switch to tactical. Confirm that:
- the opponent shown is Team B, with no opponent or week picker;
- the rebound Win % is near 100%;
- the projected You / Opp totals equal the week-to-date values plus the projected remaining
  games.

**Acceptance Scenarios**:

1. **Given** an imported `matchup.csv`, **When** I select my team and switch to tactical,
   **Then** my opponent and the matchup period come from the file. There are no opponent or week
   controls.
2. **Given** I switch to a different team, **When** tactical is shown, **Then** it shows that
   team's current matchup.
3. **Given** the current matchup, **When** results are projected, **Then** each team's total in
   every counting category equals its week-to-date actual plus its simulated remaining games.
   FG% and FT% are computed from total makes ÷ total attempts.
4. **Given** the current matchup, **When** Chance to Win, the Per Category Difference table and
   the Category Breakdown are shown, **Then** all of them use the whole-matchup totals.
5. **Given** no games remain for either team, **When** tactical is shown, **Then** the results
   equal the week-to-date actuals. Each category is won, lost or tied with certainty, and Chance
   to Win is 0%, 50% or 100%.
6. **Given** I make hypothetical roster moves, **When** results update, **Then** only the
   remaining games change. Week-to-date actuals stay with the team that earned them.
7. **Given** my team dropped a player on Wednesday after he played Monday and Tuesday, **When**
   results are projected, **Then**:
   - his Monday and Tuesday stats count for my team;
   - none of his later games do.
8. **Given** that player was picked up by my opponent, **When** results are projected, **Then**
   his stats and remaining games for my opponent count only for my opponent. No game of his
   counts for both teams.

---

### User Story 2 - Import the current matchup state (Priority: P1)

As the league's data maintainer, I import `matchup.csv` the same way I import the roster file.
The tool reports what it loaded and rejects inconsistent files.

**Why this priority**: without the data, US1 can't happen.

**Independent Test**: Import a `matchup.csv` for the current week. Confirm that:
- every team appears in exactly one pairing;
- every player who earned stats for a team has a row for it, including players since dropped;
- importing again replaces the previous state;
- the summary lists the period, the as-of time, the pairings, and the rostered and dropped
  counts per team.

**Acceptance Scenarios**:

1. **Given** a `matchup.csv`, **When** it is imported, **Then** it stores, for the league:
   - one current matchup state: the period, the as-of time, and the pairings;
   - one row per (team, player), with a status (rostered or dropped) and the week-to-date totals
     of every base statistic the scoring format needs (for 9cat: FGM, FGA, FTM, FTA, 3PM, PTS,
     REB, AST, STL, BLK, TO).
2. **Given** a file naming an unknown team or a player who can't be matched, **When** it is
   imported, **Then** the import fails with a clear message and nothing is stored.
3. **Given** a file where a team has no opponent, more than one opponent, or plays itself,
   **When** it is imported, **Then** the import fails.
4. **Given** a file where a player is rostered on two teams, **When** it is imported, **Then**
   the import fails. A player is rostered on at most one team, but may be dropped by several.
5. **Given** a file missing a statistic the scoring format needs, **When** it is imported,
   **Then** the import fails and names the missing column.
6. **Given** a newer `matchup.csv`, **When** it is imported, **Then** it replaces the league's
   current matchup state.

---

### User Story 3 - Know where the matchup stands now (Priority: P2)

As a league member, I can see the current score next to the projection, so I can tell how much of
the forecast is already settled.

**Why this priority**: the projection is more trustworthy with the actual standing beside it, but
the tool works without it.

**Independent Test**: In tactical mode, confirm that:
- the headline shows the current category score (e.g. "Now 5–3–1") and the as-of time;
- the Per Category Difference table shows both teams' week-to-date values;
- players dropped this week appear in the Roster marked "Dropped".

**Acceptance Scenarios**:

1. **Given** the current matchup, **When** I view the tactical headline, **Then** it shows the
   opponent, the period, the current category score from the actuals, and the as-of time.
2. **Given** the current matchup, **When** I view the Per Category Difference table, **Then**
   each category shows both teams' week-to-date values alongside the projected final values.
3. **Given** my team dropped a player this period, **When** I view the Roster in tactical mode,
   **Then** he is listed after the current players, marked "Dropped", with no games remaining.
4. **Given** tactical mode, **When** I look where the H2H table is in strategic mode, **Then** I
   see my opponent's roster instead:
   - it has the same columns as my roster (player, position, G), with reserve slots muted and
     status shown;
   - it lists the opponent's dropped players, marked "Dropped";
   - it has no drop buttons or other move controls, because hypothetical moves apply only to
     my team.
5. **Given** the tactical help (feature 004), **When** I open it, **Then**:
   - it explains that tactical is always the current matchup from the imported file;
   - it explains that totals are actual-so-far plus projected remaining games;
   - the settings help no longer lists vs or Week.

---

### Edge Cases

- **No matchup imported:** tactical mode is unavailable. The toggle is disabled, with a tooltip
  saying to import `matchup.csv`. Strategic still works.
- **Period over:** if the as-of time is after the period's end, results are final (US1 scenario
  5), and the headline marks the matchup as final.
- **Snapshot time vs. remaining games:** only games after the as-of time count as remaining, so a
  game is never both counted and simulated. A date-only as-of means all of that date's games
  are included.
- **Stale state:** completed games after the as-of time are in neither the actuals nor the
  simulation. The headline shows the as-of time so the user can re-import.
- **The file and the roster file disagree:**
  - **The file says dropped, but the roster file lists the player:** the file wins, his
    remaining games aren't simulated, and a notice names him.
  - **The file says rostered, but the roster file doesn't list him:** the roster file wins for
    remaining games, so he gets none. His actuals still count, and a notice names him.
- **Players with no stats yet:** a rostered player who hasn't played may have zero totals or no
  row; both mean zero actuals.
- **Dropped and re-added by the same team:** one rostered row for that team, with all his stats
  for it.
- **Zero attempts:** FG% or FT% shows "–" as today.
- **Saved sessions:** a saved session that still holds an opponent or week from before this
  feature ignores them.

## Requirements *(mandatory)*

### Functional Requirements

**Import**

- **FR-001**: The system MUST import a `matchup.csv`, separate from the roster file, holding the
  league's current matchup state:
  - the period's start and end dates;
  - the as-of time;
  - the pairings;
  - per (team, player): a status of rostered or dropped, and week-to-date totals for every base
    statistic of the scoring format.
- **FR-002**: The import MUST be all-or-nothing. It fails with a clear message on any of:
  unknown teams, unmatched players, invalid pairings, a player rostered on more than one team,
  missing statistics, or malformed values.
- **FR-003**: A newer import MUST replace the league's current matchup state. Only one current
  matchup state exists per league.
- **FR-004**: The matchup state MUST live in the same shared data store as the other league
  data. The import stays separate from the engine and tools, as the roster import does.

**Tactical = current matchup**

- **FR-005**: Tactical mode MUST show the selected team's current matchup. The opponent and the
  period come from the imported state. The opponent and week controls MUST be removed.
- **FR-006**: A team's week-to-date actual per base statistic MUST be the sum of all its rows,
  rostered and dropped.
- **FR-007**: Each team's simulated total MUST be its actual plus its simulated remaining games,
  in every simulation. Ratio categories use combined makes ÷ combined attempts.
- **FR-008**: Remaining games MUST be those scheduled after the as-of time and on or before the
  period's end. They are simulated only for players currently on the team, so a player marked
  dropped contributes none. Each player's remaining games count for at most one team.
- **FR-009**: Chance to Win, the Per Category Difference table and the Category Breakdown MUST use
  the whole-matchup totals.
- **FR-010**: Hypothetical roster moves MUST change only the remaining-games part.
- **FR-011**: When no games remain, the results MUST be determined by the actuals alone.
- **FR-012**: Without an imported matchup, tactical mode MUST be unavailable, with an explanation
  of why.
- **FR-013**: Strategic mode MUST be unaffected.

**Display**

- **FR-014**: The tactical headline MUST show the opponent, the period, the current category
  score and the as-of time. It is marked final once the period is over.
- **FR-015**: The Per Category Difference table MUST show both teams' week-to-date values next to
  the projected finals.
- **FR-016**: The tactical Roster MUST list players dropped this period after the current
  players, marked "Dropped". They can't be dropped again or used in moves.
- **FR-016a**: In tactical mode, the H2H table MUST be replaced by the opponent's roster, titled
  with the opponent's team name. It's read-only, with no drop or move controls, and shows the
  opponent's players dropped this period marked "Dropped". Strategic mode keeps the H2H table.
- **FR-017**: Disagreements between the matchup state and the roster file MUST raise a notice
  naming the players involved.
- **FR-018**: The help (feature 004) MUST be updated:
  - the settings help drops vs and Week;
  - the Strategic / Tactical help says tactical is the current matchup, with actual plus
    projected totals;
  - the tactical headline and table help mention the current score and the week-to-date values;
  - the opponent's roster gets its own help, which says it is read-only.
- **FR-019**: The move-impact highlighting (feature 003) MUST keep working. Before and after
  share the same actuals.

### Key Entities

- **Current matchup state**: per league, the period (start and end), the as-of time, and the
  pairings. It is replaced on each import.
- **Pairing**: two teams playing each other in the current period. Each team is in exactly one.
- **Player week-to-date contribution**: per team and player, a status (rostered or dropped) and
  the base-statistic totals (including makes and attempts) he earned for that team this period.
  A player may have rows for several teams but is rostered on at most one.
- **Team week-to-date totals** (derived): the sum of a team's player contributions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In tactical mode, the opponent shown matches the imported pairing for 100% of
  teams, with no opponent or week control on the page.
- **SC-002**: For every category, the projected mean total equals the week-to-date value plus the
  mean of the simulated remaining games, within rounding.
- **SC-003**: With no games remaining, Chance to Win and every category's Win % are exactly 0%,
  50% or 100%, and they match the actual category results in 100% of categories.
- **SC-004**: A dropped player's stats count for his former team, and none of his remaining
  games do. Verified with a fixture where he's picked up by the opponent: no game is counted
  twice.
- **SC-005**: A full-league `matchup.csv` (18 teams) imports in under 5 seconds and leaves exactly
  one current matchup state.
- **SC-006**: Strategic results are identical before and after this feature for the same inputs
  and seed.
- **SC-007**: A user can read the opponent, the current category score and the as-of time from
  the headline without opening another screen.

## Assumptions

- **Where the file comes from:** `matchup.csv` is produced by the same exporter that writes the
  roster file and sits next to it (`~/dev/ccsv-rumble-page/data/`). It uses the same team and
  player identifiers. The exporter is outside this repository and must be extended to write the
  file; the columns are fixed in the plan.
- **Platform stats:** each player's week-to-date stats for a team are taken from the platform
  as-is. That includes only games he played for that team, and only in an active lineup slot.
  The tool never rebuilds actuals from NBA game logs.
- **Makes and attempts:** the file reports makes and attempts (FGM/FGA, FTM/FTA), not just
  percentages.
- **Dropped players:** the exporter can list players each team dropped during the current period,
  with their stats for that team.
- **Current only:** past and future weeks aren't supported in tactical mode, so there's no
  history of matchup states.
- **Remaining-games model:** remaining-games simulation is unchanged (each player plays every
  remaining scheduled game).
- **Opponent moves:** you can't make hypothetical moves for the opponent. Their remaining games
  come from their current roster as imported.
