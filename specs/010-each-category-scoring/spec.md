# Feature Specification: H2H Each-Category Scoring

**Feature Branch**: `010-each-category-scoring`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "look at https://github.com/dougkang/xlift/issues/9 and implement"
(issue #9: "matchups yield W-L-T per category, not a single W or single L")

## Overview

The league scores **H2H Each Category**: every category of a weekly matchup goes into the
standings as its own W, L or T, so a week counts as something like 6–3–0. The app, and
[the overview](../../docs/overview.md), assume **H2H Most Categories** instead: whoever wins more
categories gets one W for the week.

The model doesn't need to change. Under each-category scoring, the number that decides the
standings is the **expected category record**: for each category and opponent, P(win) + ½·P(tie).
The radar's Win % and xLift already compute exactly that. What changes is what the app shows and
calls a "result":

- the headline record, in both modes;
- the H2H table;
- the before/after changes for roster moves;
- the help and the docs.

How a matchup turns into standings is a rule of the league's scoring format (Constitution II).
Leagues that score Most Categories keep today's behavior, unchanged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See my projected standings record across the league (Priority: P1)

A manager in an each-category league opens Impact Analysis in Strategic mode. The headline shows
the category record they're projected to earn if they played every other team once, e.g.
"58–45–5", and their standings win %. That is the number that moves them up the table.

**Why this priority**: the headline is the first thing a manager reads. Today it shows a matchup
record that doesn't exist in this league, so it measures the wrong goal.

**Independent Test**: load an each-category league, open Strategic, and check that the headline
is an expected category record summed over all opponents, with a win % of (W + ½T) ÷ total.

**Acceptance Scenarios**:

1. **Given** an each-category league in Strategic mode, **Then** the headline shows the expected
   category W–L–T summed over every other team, in whole numbers, labeled **Aggregated Record**:
   the combined H2H score, equal to the H2H Total row.
2. **Given** that headline, **Then** it also shows the standings win %, (W + ½T) ÷ (W + L + T),
   as a whole percentage.
3. **Given** a most-categories league, **Then** the headline is unchanged: the matchup W–L–T
   ("Aggregated Record").
4. **Given** the expected record, **Then** W + L + T equals the number of categories times the
   number of opponents (within rounding).

---

### User Story 2 - See how a roster move changes my standings (Priority: P1)

The manager adds or drops a player. The headline and each H2H row show the change in expected
category wins, so even a small gain (0.3 of a win a week) is visible.

**Why this priority**: deciding on moves is what the tool is for. Today's change markers count
whole wins and matchup flips (loss→win), which mean nothing in this league, so a real gain can show
as no change.

**Independent Test**: make a move that helps one category, and check that the headline and H2H
rows show a signed change in expected wins, colored better or worse.

**Acceptance Scenarios**:

1. **Given** an each-category league and a roster move, **Then** the headline shows the change in
   expected wins (e.g. "+1"), the difference of the whole-number records, green if more and red
   if fewer, and the change in
   win %.
2. **Given** a move that leaves the whole-number wins the same, **Then** no change in wins is
   shown; the win % change still shows it if it moves a whole point.
3. **Given** each H2H row, **Then** it shows the change in that opponent's expected category wins,
   and no matchup flip markers.
4. **Given** a most-categories league, **Then** the changes are as today, including loss↔win
   flips.

---

### User Story 3 - See this week's projected category record (Priority: P2)

In Tactical mode, the manager sees the category record they're projected to finish the current
week with: the score so far plus the games left, e.g. "6–3–0", instead of a chance to win
the matchup.

**Why this priority**: the tactical headline drives streaming decisions. In an each-category
league every close category is worth a full W all week, so the expected record is the number to
push.

**Independent Test**: open Tactical for an each-category league with a loaded matchup, and check
that the headline is the expected category record for this week, and that a streaming move shows
its change in expected wins.

**Acceptance Scenarios**:

1. **Given** an each-category league in Tactical mode with this week's matchup loaded, **Then** the
   headline shows the projected category W–L–T for this week, in whole numbers, labeled as a
   projected record.
2. **Given** the week is over, **Then** the projected record equals the final category score.
3. **Given** a move, **Then** the headline shows the change in expected wins in whole numbers.
4. **Given** a most-categories league, **Then** the headline is "Chance to Win" as today.

---

### User Story 4 - Read the H2H table as category records (Priority: P2)

In Strategic mode, the H2H table lists each opponent with the expected category record against
them. The Total row sums them, and it matches the headline.

**Why this priority**: the table explains the headline opponent by opponent. Its Win and Result
columns describe a matchup winner that this league doesn't have.

**Independent Test**: in an each-category league, check the H2H columns, and that the Total row
equals the headline record.

**Acceptance Scenarios**:

1. **Given** an each-category league, **Then** each H2H row shows the opponent, the expected
   category W–L–T against them in whole numbers, with no win % column.
2. **Given** the H2H table, **Then** it has no matchup Win or Result column.
3. **Given** the Total row, **Then** it shows the summed expected record, equal to the
   headline.
4. **Given** a most-categories league, **Then** the table is unchanged.

---

### User Story 5 - Set the league's scoring rule (Priority: P2)

The data maintainer sets whether a league scores each category or most categories. The league
keeps that setting through the daily data refresh.

**Why this priority**: the Yahoo capture doesn't record the scoring rule, so it must be set once,
by hand, for the app to show the right numbers.

**Independent Test**: set an existing league to each-category, run a roster refresh without
naming a format, and check the league still uses each-category scoring.

**Acceptance Scenarios**:

1. **Given** the maintainer names the each-category format when loading a league's rosters,
   **Then** the league uses it from then on.
2. **Given** a later roster load that names no format, **Then** the league keeps its format.
3. **Given** a format name the app doesn't know, **Then** the load is refused with a message
   listing the formats it knows.

---

### Edge Cases

- **Ties**: a tied category counts as half a win in the win %, and is still reported as a T in the
  record (Constitution I). Low-count categories (STL, BLK) tie often, so expected T is often
  well above zero.
- **Two-team league**: the strategic record is one opponent's expected category record.
- **Missing ratio** (no attempts in a simulation): handled as today; that simulation's category
  is a tie.
- **Matchup not loaded** (Tactical): the existing notice shows, and no headline record is shown.
- **Unsupported format**: the existing notice shows.
- **Rounding**: records show whole categories. Each opponent's W + L + T is exactly the category
  count, and the Total is the sum of the rows, so a small expected T (e.g. 0.2 against every
  opponent) can show as 0. The win % is computed from unrounded values.
- **Before/after across a format change**: changes compare two results of the same league, so the
  format can't differ between them.

## Requirements *(mandatory)*

### Functional Requirements

**The scoring rule**

- **FR-001**: Each scoring format MUST declare how a matchup turns into standings:
  **most categories** (one W, L or T per matchup, as today) or **each category** (one W, L or T
  per category).
- **FR-002**: The app MUST offer a 9-category each-category format alongside the existing
  9-category most-categories format, with the same categories, aggregation and directions.
- **FR-003**: Tools, the API and the frontend MUST read the standings rule from the format; they
  MUST NOT check which format is loaded by its name.
- **FR-004**: Under each-category, the expected record against an opponent MUST be, per category,
  W = P(win), L = P(loss), T = P(tie) over the simulations, summed over categories. Each
  opponent's W + L + T MUST equal the number of categories.
- **FR-005**: The standings win % MUST be (W + ½T) ÷ (W + L + T), from unrounded values.
- **FR-006**: Every result MUST say which standings rule produced it, so the page can label it.

**Strategic headline**

- **FR-007**: Under each-category, the strategic headline, **Aggregated Record**, MUST be the
  combined H2H score: the expected category W–L–T summed over every other team (the H2H Total),
  in whole numbers, and the standings win %.
- **FR-008**: Under most categories, the strategic headline MUST be unchanged.

**Tactical headline**

- **FR-009**: Under each-category, the tactical headline MUST show this week's expected category
  W–L–T against the current opponent (week-to-date totals plus the games left), in whole numbers.
- **FR-010**: Under most categories, the tactical headline MUST be unchanged ("Chance to Win").
- **FR-011**: The current score line ("Now 4–4–1") MUST be unchanged under both rules.

**H2H table (Strategic)**

- **FR-012**: Under each-category, each H2H row MUST show the expected category W–L–T against that
  opponent in whole numbers; the matchup Win and Result columns and a win % column MUST NOT appear.
- **FR-013**: Under each-category, the Total row MUST show the summed expected record,
  equal to the headline.
- **FR-014**: Under most categories, the H2H table MUST be unchanged.

**Changes from roster moves**

- **FR-015**: Under each-category, the headline (both modes) MUST show the change in expected wins
  in whole numbers, and in Strategic the change in win % in whole points, each colored better or
  worse and hidden when zero at that precision.
- **FR-016**: Under each-category, each H2H row and the Total row MUST show the change in expected
  wins in whole numbers; there MUST be no matchup flip markers.
- **FR-017**: Under most categories, all changes MUST be as today.
- **FR-018**: Per-category changes (rank, average, Win %, win probability) MUST be unchanged under
  both rules; they already show which categories moved.

**Unchanged**

- **FR-019**: Projections, simulation, the radar, the category table, the Category Breakdown,
  xLift and Player Analysis MUST be unchanged under both rules.
- **FR-020**: For a most-categories league, every analysis result MUST be identical to today's.

**Data maintenance**

- **FR-021**: The maintainer MUST be able to set a league's format when loading its rosters; a
  later load that names no format MUST keep it; an unknown format MUST be refused with the list
  of known formats.

**Help and docs**

- **FR-022**: The help for the headline and the H2H table MUST explain the rule in force in plain
  words: under each-category, that every category counts as a W, L or T in the standings, that
  records are expected values, and that a tie counts half in the win %. Help MUST NOT name data
  files.
- **FR-023**: The domain docs MUST describe both rules, state that the league scores each
  category, and revise the strategy notes: under each-category a 5–4 week is middling, and
  punting costs more because every category counts the same.

### Key Entities

- **Standings rule**: declared by a scoring format: most categories or each category.
- **Expected record**: W, L, T as fractional expected counts of categories; with its win %.
- **Opponent row**: one opponent's expected category record (each-category), or today's
  matchup row (most categories).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In each-category Strategic mode, the headline win % equals the mean of the selected
  team's per-category Win % on the radar, within 0.5 percentage points (both are P(win) + ½P(tie)
  averaged over opponents and categories, so they are the same number).
- **SC-002**: For every opponent, the expected W + L + T equals the number of categories within
  0.001 before rounding.
- **SC-003**: A roster move that changes the whole-number expected wins shows that change in the
  headline 100% of the time.
- **SC-004**: For a most-categories league, every analysis result, in both modes, with and without
  moves, is identical to the result before this feature.
- **SC-005**: The H2H Total row equals the headline record at display precision in 100% of
  each-category strategic views.
- **SC-006**: A manager can read their projected standings win % from the headline without
  opening help or adding numbers.

## Assumptions

- **The league scores each category.** The issue's reading of the user's note; the Yahoo capture
  doesn't record it, so the maintainer sets it (FR-021).
- **Rule on the format.** The issue asks to decide between a new format and a rule the format
  declares; this spec asks for both: the rule is declared by each format, and a new each-category
  9-category format declares it. Which parts live where is a plan decision.
- **No distribution of categories won.** The issue suggests a distribution of categories won could
  sit beside the tactical headline. It's left for later; the expected record is the headline.
- **Equal opponent weights.** The strategic record and xLift weigh every opponent equally. Weighting
  by the opponents left on the schedule is a later improvement.
- **The backtest is out of scope.** The analysis backtest script (issue item 9) is the user's
  uncommitted analysis work and isn't changed here.
- **The daily refresh script isn't changed.** The format is set once by the maintainer and kept by
  later loads.
- **Display precision.** Records in whole numbers, win % to whole percentages, as elsewhere in the
  app.
