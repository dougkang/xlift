# Feature Specification: Focus on an H2H Opponent

**Feature Branch**: `011-h2h-opponent-focus`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "clicking on an opponent on h2h should hide other radars other than the current team and selected team, and change league average stats to the selected team's stat. we should similarly change the league distribution in the category breakdown to the selected team's distribution."

## Overview

In Strategic mode, Impact Analysis compares the manager's team with the whole league: the radar
overlays every team and the League Average, the Per Category Ranking table shows the league
average beside the team's own, and the Category Breakdown overlays the league's distribution.
The H2H table lists each opponent's projected category record, but from there the manager can't
see *why* a matchup goes the way it does.

This feature lets the manager click an opponent in the H2H table to **focus** on them. The page
then compares the team with that one opponent instead of the league:

- the radar shows only the manager's team and the focused opponent;
- the **League** column of the Per Category Ranking becomes that opponent's averages;
- the Category Breakdown's league distribution becomes that opponent's distribution.

Clicking the opponent again returns to the league view. Focus changes only which comparison is
drawn; the projections, the records and every number about the manager's own team stay the same.

"Your team" below is the team selected in the team picker; "the focused opponent" is the one
clicked in H2H.

## Clarifications

### Session 2026-10-29

- Q: When focused on an opponent, should the Category Breakdown still show the League Leader
  alongside your team and the opponent? → A: Keep the League Leader (or Next Best): each chart
  shows your team, the opponent and the Leader.
- Q: Under focus, should the Per Category Ranking's Win % column switch to your chance of beating
  the focused opponent in each category? → A: Yes, switch it, but keep the header "Win %".
- Q: Under focus, should the radar's Win % view also switch to the chances against the focused
  opponent? → A: Yes: your chance of beating them per category, and theirs as the mirror (1 − yours).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare my team with one opponent (Priority: P1)

A manager sees in H2H that they're projected to lose to Triton Aggies 3–6–0. They click that row.
The radar now shows only their team and Triton Aggies, the League column shows Triton Aggies'
averages, and each breakdown chart shows Triton Aggies' distribution next to theirs. They can see
at a glance which categories the matchup turns on.

**Why this priority**: this is the request, and it turns H2H from a list of results into an
explanation of each one.

**Independent Test**: click an opponent row in H2H, and check the radar, the League column and the
breakdown show that opponent in place of the league.

**Acceptance Scenarios**:

1. **Given** Strategic mode with no focus, **When** the manager clicks an opponent's row in H2H,
   **Then** that row is marked as focused.
2. **Given** a focused opponent, **Then** the radar shows only two teams, the manager's and the
   focused opponent's, with the opponent drawn the way Tactical mode draws an opponent; other teams
   and the League Average shape are hidden. On the **Win %** view, each spoke is the chance of
   winning that category in this matchup: the manager's P(win) + ½·P(tie) against the opponent,
   and the opponent's as its mirror (1 − the manager's); Rank and Average stay league-wide.
3. **Given** a focused opponent, **Then** the Per Category Ranking's **League** column shows the
   focused opponent's projected average in each category, and its header names the opponent
   instead of "League".
4. **Given** a focused opponent, **Then** the Per Category Ranking's **Win %** column shows the
   manager's chance of beating that opponent in each category (ties count half), under the same
   "Win %" header.
5. **Given** a focused opponent, **Then** each Category Breakdown chart shows the focused
   opponent's distribution and average in place of the League Average's, labeled with the
   opponent's name, drawn the way Tactical mode draws an opponent. The League Leader (or Next
   Best) stays.
6. **Given** a focused opponent, **Then** the H2H table, the headline, the roster and the player
   picker are unchanged.

---

### User Story 2 - Return to the league view (Priority: P1)

The manager is done looking at one opponent and wants the league picture back.

**Why this priority**: focus must be easy to leave, or the league comparison is lost.

**Independent Test**: focus an opponent, then clear it, and check the page is exactly the
unfocused view.

**Acceptance Scenarios**:

1. **Given** a focused opponent, **When** the manager clicks the same row again, **Then** focus is
   cleared and the radar, the League column and the breakdown return to the league view.
2. **Given** a focused opponent, **When** the manager clicks a different opponent's row, **Then**
   focus moves to that opponent.
3. **Given** a focused opponent, **When** the manager switches to Tactical mode, picks another
   team or another league, **Then** focus is cleared.

---

### User Story 3 - Keep the focus while testing moves (Priority: P2)

With an opponent focused, the manager adds or drops a player to see how it changes that matchup.

**Why this priority**: the point of focusing is often to find the move that flips a matchup.

**Independent Test**: focus an opponent, make a roster move, and check focus stays and the
before/after markers still show.

**Acceptance Scenarios**:

1. **Given** a focused opponent, **When** the manager makes or undoes a roster move, **Then** the
   focus stays on the same opponent.
2. **Given** a focused opponent and a move, **Then** the before-move markers for the manager's own
   team (the dotted "(before)" distribution and the radar's before shape) still show.
3. **Given** a move that involves the focused opponent (a trade with them), **Then** their radar
   shape, averages and distribution reflect the move.

---

### Edge Cases

- **Tactical mode**: H2H isn't shown, so there's nothing to click; Tactical already compares with
  one opponent.
- **Most-categories and each-category leagues**: focus works the same under both; it doesn't
  depend on how records are scored.
- **The focused opponent leads a category** (or is Next Best when your team leads): the opponent
  and the Leader are the same team, so that chart draws them once, as the opponent (see FR-008).
- **Missing value** (e.g. an opponent with no FG attempts in a category): shown as "–", as
  elsewhere.
- **Before/after changes in the League and Win % columns**: under focus, the League column's change
  marker shows the change in the opponent's average (only non-zero when a move involves them), and
  the Win % column's shows the change in the chance of beating that opponent.
- **Help**: the radar, Per Category Ranking and Category Breakdown help explain that clicking an
  H2H row focuses on that opponent.
- **Reload**: focus isn't kept across a page reload.

## Requirements *(mandatory)*

### Functional Requirements

**Focusing**

- **FR-001**: In Strategic mode, each H2H opponent row MUST be clickable (and reachable and
  activatable from the keyboard) to focus on that opponent.
- **FR-002**: The focused row MUST be marked with the style guide's selected-row treatment (yellow
  background), the same as the current opponent's row elsewhere.
- **FR-003**: Clicking the focused row again MUST clear focus; clicking another row MUST move
  focus to it.
- **FR-004**: Focus MUST clear when the mode, team or league changes; it MUST stay through roster
  moves, undo and reset of moves, window and Fragility Penalty changes.

**Radar**

- **FR-005**: Under focus, the radar MUST show only the manager's team and the focused opponent,
  on every radar scale (Rank, Average, Win %); other teams and the League Average shape MUST be
  hidden. The opponent MUST be drawn in the style Tactical mode uses for an opponent.
- **FR-005a**: Under focus, the radar's **Win %** view MUST plot, per category, the manager's
  chance of beating the focused opponent, P(win) + ½·P(tie), and the opponent's chance as
  1 − the manager's, equal to the Per Category Ranking's Win % column. The **Rank** and **Average**
  views MUST stay league-wide (each team's league rank and league min-max position).
- **FR-005b**: The radar's area scores on each tab MUST stay league-wide under focus (they rate the
  manager's team against the league, not one matchup).
- **FR-006**: Under focus, the radar legend MUST name the focused opponent.

**Per Category Ranking**

- **FR-007**: Under focus, the **League** column MUST show the focused opponent's projected average
  per category, with the header naming the opponent (shortened if needed, full name on hover);
  the **Win %** column MUST show the manager's chance of beating the focused opponent in each
  category, P(win) + ½·P(tie), keeping the header "Win %"; the Rank, Avg and Leader columns MUST
  be unchanged.

**Category Breakdown**

- **FR-008**: Under focus, each category chart MUST show the focused opponent's simulated
  distribution and average in place of the League Average's, in the style Tactical mode uses for
  an opponent and labeled with the opponent's name. The League Leader (or Next Best) MUST stay as
  it is; when it is the focused opponent, the chart MUST draw that team once, as the opponent.
- **FR-009**: Under focus, the league-shape line and gap bars below each chart MUST be unchanged:
  they describe the whole league, not one matchup.

**Unchanged**

- **FR-010**: Focus MUST NOT change any projection, record, xLift, or the H2H table's contents.
  Of the manager's team's numbers, only the Win % values, on the radar (FR-005a) and in the Per
  Category Ranking (FR-007), and their change markers become matchup-specific; every other number
  and change marker for the manager's team MUST be unchanged.
- **FR-011**: The opponent's numbers shown under focus MUST be the same simulation's numbers used
  for the H2H row (same projections, settings and seed); the page MUST NOT compute statistics
  itself.

**Help**

- **FR-012**: The H2H help MUST say that clicking a row focuses on that opponent and clicking it
  again returns to the league; the radar, Per Category Ranking and Category Breakdown help MUST say
  what changes under focus, including that Win % becomes the chance of beating the focused
  opponent. Help MUST NOT name data files.

### Key Entities

- **Focused opponent**: at most one opponent at a time, chosen from H2H; page state only, cleared
  on mode, team or league change.
- **Opponent comparison**: per category, the focused opponent's projected average, simulated
  distribution, and the manager's chance of beating them, from the same analysis as the H2H row.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After clicking an opponent, the radar shows exactly 2 team shapes, the League
  column's values equal that opponent's projected averages, and the Win % column's values equal
  the category odds behind that opponent's H2H row, in 100% of categories.
- **SC-002**: Under focus, each of the 9 breakdown charts shows the focused opponent's
  distribution, and its marked average equals the League column's value for that category.
- **SC-003**: Focusing or clearing focus updates the page within 0.5 seconds of the click on the
  real league.
- **SC-004**: Clearing focus restores a page identical to the unfocused view.
- **SC-005**: Every number about the manager's own team, except Win % on the radar and in the Per
  Category Ranking, is identical with and without focus.

## Assumptions

- **Strategic only.** H2H appears only in Strategic mode; Tactical already compares with one
  opponent and is unchanged.
- **Rank and Leader columns unchanged.** They describe the league.
- **Area scores unchanged.** The radar's per-tab area scores keep rating the team against the
  league under focus; a matchup area score would be a new measure.
- **Click target is the row.** The whole opponent row is the target; no separate button.
- **Builds on 010.** The H2H table is the one from feature 010 (each-category and most-categories
  layouts).
