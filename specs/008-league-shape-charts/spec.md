# Feature Specification: League Shape Charts in the Category Breakdown

**Feature Branch**: `008-league-shape-charts`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Add two league-shape charts per category to the Impact Analysis Category Breakdown, as in the player rankings report: (1) League shape — each team's projected per-period category value plotted against its rank (rank on x, value on y, line through the dots), and (2) Against null — bars of the gap needed to reach each rank (value at rank r minus value at rank r+1), with a line overlay of the gap a normally distributed league of the same size and spread would show (Blom's expected normal order statistics × the category's standard deviation across teams). The selected team must be marked in both charts: its dot in League shape, and in Against null the gap it must close to climb one rank (and the cushion to the team below). Values come from the analysis's projected averages and reflect hypothetical moves. The frontend only renders values the backend computes."

## Overview

The Category Breakdown shows the spread of the selected team's simulated weekly totals in each
category, with the league leader and league average overlaid. It doesn't show where the other
teams sit, so a manager can't see whether a rank is cheap to gain (rivals bunched just above)
or expensive (a big gap to the next team).

The player rankings report answers that with two charts per category, and they've proved the
most useful views there:

- **League shape**: every team's projected value in the category, ordered by rank, joined by a
  line. Even spacing means every place costs the same; clusters and cliffs show where ranks are
  cheap or expensive.
- **Against null**: for each rank, the gap a team must close to reach it (bars), against the gap
  a league of the same size and spread would show if teams were normally distributed (a line).
  Bars above the line are unusually large gaps; bars below it are unusually tight clusters.

This feature adds both charts to each category of the Category Breakdown, with the selected
team marked, so the manager sees which categories offer a cheap rank and which don't.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See where my team sits in each category's league shape (Priority: P1)

A manager opens the Category Breakdown and, for each category, sees every team's projected value
ordered by rank, with their own team's dot marked. They can see at a glance whether the teams
just above are close (a rank is within reach) or far away.

**Why this priority**: it's the core view the manager asked for and the simplest to read; it
answers "is the next rank close?" on its own.

**Independent Test**: open a strategic analysis and check that each category shows a League
shape chart with one point per team, ordered by rank, and the selected team's point marked.

**Acceptance Scenarios**:

1. **Given** a strategic analysis for a team, **When** the Category Breakdown is shown, **Then**
   each of the nine categories has a League shape chart with one point per team in the league,
   at x = the team's place in that category and y = its projected per-period value.
2. **Given** that chart, **When** the manager looks for their team, **Then** exactly one point is
   marked as the selected team, in the selected team's color, and its place, and the rank shown
   on hover, match the team's rank in the Per Category Ranking table (they differ only when teams
   tie).
3. **Given** a point, **When** the manager hovers it, **Then** they see the team's name, rank and
   value.
4. **Given** a lower-is-better category (TO), **When** shown, **Then** rank 1 is the team with the
   fewest turnovers, so the values rise from left to right.

---

### User Story 2 - See which ranks are unusually cheap or expensive (Priority: P1)

For each category the manager also sees the gaps between consecutive ranks as bars, with the gap
a normally distributed league would show as a line. Their own team's next step up (the gap to
climb one rank) and its cushion (the gap to the team below) are marked.

**Why this priority**: it turns the league shape into the decision the manager makes: chase this
category (a small, below-normal gap to climb) or not (a cliff).

**Independent Test**: open a strategic analysis and check that each category shows an Against
null chart with one bar per pair of adjacent ranks, a null line, and the selected team's climb
and cushion bars marked.

**Acceptance Scenarios**:

1. **Given** a league of N teams, **When** the Against null chart is shown for a category,
   **Then** it has N − 1 bars; bar *r* is the gap between the teams at ranks *r* and *r* + 1, in
   the category's units, never negative.
2. **Given** the same chart, **Then** a line shows, for each *r*, the gap a normal league of N
   teams with the same spread would have between ranks *r* and *r* + 1.
3. **Given** the selected team at rank *R* (1 < *R* < N), **Then** bar *R* − 1 (the gap to climb
   to rank *R* − 1) is marked as the climb in the selected team's color, and bar *R* (the gap to
   the team below) is marked as the cushion in a lighter shade of it.
4. **Given** the selected team is first, **Then** only the cushion is marked; **given** it is
   last, only the climb is marked.
5. **Given** a bar, **When** the manager hovers it, **Then** they see the rank it leads to, the
   gap and the null gap.

---

### User Story 3 - See how moves change the shape (Priority: P2)

After a hypothetical move, both charts reflect the moved rosters. The selected team's position
before the move is also shown in League shape, so the manager sees how far the move shifts them.

**Why this priority**: moves are the dashboard's purpose; the charts must follow them, and the
before-position matches how the breakdown already shows "before" distributions.

**Independent Test**: make a move that changes the team's rank in a category, and check that the
charts update, the marked team point moves to the new rank, and a before marker sits at the old
position.

**Acceptance Scenarios**:

1. **Given** a move that changes the team's values, **When** the analysis updates, **Then** both
   charts use the moved league's values and ranks.
2. **Given** moves are in effect, **Then** League shape also shows the selected team's
   pre-move rank and value as a distinct "before" marker; without moves, no before marker.
3. **Given** the moves are reset, **Then** the charts return to the original league.

---

### Edge Cases

- **Ties**: teams with equal values take consecutive ranks in a fixed order (by team), and the gap
  between them is 0. The selected team's marked bars follow its assigned rank.
- **Missing values**: a team with no value in a category (e.g. no free-throw attempts, so no FT%)
  is left out of that category's charts; N is the number of teams with a value. With fewer than
  three teams with values, the category shows no Against null chart (no meaningful spread).
- **No spread**: if every team has the same value, all gaps and the null line are 0.
- **Ratio categories** (FG%, FT%): values and gaps both display in the dashboard's three-decimal
  style (a value .473, a gap .012).
- **Tactical mode**: the Category Breakdown there compares the team with its current opponent;
  these league-wide charts are shown only in strategic mode (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: In strategic mode, the Category Breakdown MUST show, for each category, a League
  shape chart and an Against null chart alongside the existing distribution chart.
- **FR-002**: League shape MUST plot one point per team with a value: x = the team's place in the
  category: its rank order, 1 = best and direction-aware (fewest turnovers is 1), with tied teams
  taking adjacent places in team order; y = the team's projected
  per-period value, with a line joining the points in rank order.
- **FR-003**: The values MUST be the same projected per-period values the analysis shows
  elsewhere (the Per Category Ranking table's averages), and the ranks MUST match that table's
  ranks.
- **FR-004**: Against null MUST show, for each *r* = 1 … N − 1, a bar of the gap between the
  values at ranks *r* and *r* + 1 (absolute, in the category's units).
- **FR-005**: Against null MUST overlay, for each *r*, the null gap: the expected gap between
  ranks *r* and *r* + 1 in N draws from a normal distribution with the category's spread. It is
  the difference of consecutive expected normal order statistics (Blom's approximation,
  z_i = Φ⁻¹((i − 0.375) / (N + 0.25))) times the standard deviation (with N − 1 in the
  denominator) of the teams' values.
- **FR-006**: League shape MUST mark the selected team's point in the selected team's color;
  other teams' points MUST be neutral.
- **FR-007**: Against null MUST mark the selected team's climb (the bar leading to its rank − 1)
  in the selected team's color and its cushion (the bar from its rank to rank + 1) in a lighter
  shade, omitting whichever doesn't exist at rank 1 or rank N.
- **FR-008**: Hovering a point MUST show the team's name, rank and value; hovering a bar MUST
  show the rank it leads to, the gap and the null gap.
- **FR-009**: Both charts MUST reflect hypothetical moves (the moved league's values and ranks).
- **FR-010**: With moves in effect, League shape MUST also show the selected team's pre-move rank
  and value as a distinct before marker.
- **FR-011**: Ranks, values, gaps and null gaps MUST be computed by the analysis (backend) and
  only drawn by the dashboard; the dashboard MUST NOT compute ranks or gaps itself.
- **FR-012**: Teams without a value in a category MUST be left out of that category's charts; a
  category with fewer than three teams with values MUST omit the Against null chart.
- **FR-013**: The Category Breakdown's help MUST explain both charts (what the line and bars
  mean, and the climb and cushion marks) in plain words, within the existing help length limit
  and without mentioning file names.
- **FR-014**: The charts MUST follow the dashboard's existing style (colors, fonts, sizes) and
  stay legible at the breakdown's existing per-category width.
- **FR-015**: Tactical mode's Category Breakdown MUST be unchanged.

### Key Entities

- **League shape (per category)**: one entry per team with a value: team, rank, projected value,
  and whether it is the selected team; plus the selected team's before rank and value when moves
  are in effect.
- **Rank gaps (per category)**: one entry per adjacent rank pair *r*: the rank it leads to, the
  gap, the null gap, and a mark (climb, cushion or none).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In strategic mode, 100% of categories with at least three teams with values show
  both charts, and each chart marks the selected team exactly as FR-006 and FR-007 describe.
- **SC-002**: For every category, the League shape ranks equal the Per Category Ranking table's
  ranks, and its values equal the table's league values to display precision.
- **SC-003**: The gaps and null gaps match the rankings report's computation on the same league
  values within 0.001 of the category's units.
- **SC-004**: After a move, both charts reflect the moved league within the same update as the
  rest of the dashboard, and the before marker shows the pre-move position.
- **SC-005**: Adding the charts adds no more than 5% to an analysis's response time on the real
  league.
- **SC-006**: Tactical mode's Category Breakdown and every existing strategic number are
  unchanged.

## Assumptions

- **Strategic mode only**: the charts are league-wide comparisons, and strategic mode is the
  league-wide view; tactical mode's breakdown stays focused on the current opponent (FR-015).
  This can be revisited.
- **Values**: the analysis's projected per-period averages per team (ratio categories as ratios
  of totals), as already used by the radar and the Per Category Ranking table, rather than the
  report's expected-line totals. They're the same quantity up to simulation noise and keep the
  charts consistent with the rest of the dashboard.
- **Layout**: each category keeps its existing distribution chart; the two new charts sit with
  it in that category's block, small multiples at the same width.
- **Gaps in display units**: gaps follow each category's display convention (counting stats in
  units, ratio categories in the same style as their values).
- **No new controls**: the charts have no settings of their own.
- **Before marker**: shown for League shape only; Against null shows the moved league.
