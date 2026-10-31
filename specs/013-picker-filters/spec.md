# Feature Specification: Player Picker Filters and Category Sort

**Feature Branch**: `013-picker-filters`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "look at and implement https://github.com/dougkang/xlift/issues/8"
(issue #8: "impact analysis should allow you to search players by position, team(s); also sort
by xLIFT in specific categories")

## Clarifications

### Session 2026-10-30

- Q: "Team(s)": the player's NBA team or his fantasy team? → A: Fantasy team (who owns him:
  free agent or one of the league's teams), several at once.
- Q: Sort by one category or several? → A: Several, summed: pick any categories and players are
  ranked by their xLift summed over those.

## Overview

Impact Analysis's player picker lists everyone not on your team, ranked by xLift, with a name
search. A manager hunting for a specific kind of player (a center, a trade target on one team,
someone who helps rebounds and blocks) has to scroll and read every row.

This feature adds to the picker:

- a **Position** filter (G, F, C, several at once);
- a **Team** filter: free agents and the league's other fantasy teams, several at once;
- a **Sort by** choice of categories: when any are picked, players are ranked by their xLift
  summed over those categories instead of their total xLift.

xLift itself doesn't change ([Impact Analysis](../../docs/tool1-impact-analysis.md#xlift)); the
per-category values are the same breakdown Player Analysis draws (009).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find a player by position (Priority: P1)

A manager needs a center. They pick **C** in the picker's Position filter and see only players
who can play center, still ranked by xLift.

**Why this priority**: position is the most common constraint on a pickup.

**Independent Test**: pick C and check every listed player has C among his positions; pick G and
C and check every player has G or C.

**Acceptance Scenarios**:

1. **Given** no position picked (the default), **Then** every position is listed, as today.
2. **Given** one or more positions picked, **Then** only players with at least one of them are
   listed, in the same order as without the filter.
3. **Given** a player with no listed position, **Then** he is shown only when no position filter
   is set.

---

### User Story 2 - Look at one or more fantasy teams (Priority: P1)

A manager wants a trade target from two specific teams, or only free agents. They pick those in
the Team filter.

**Why this priority**: the picker mixes 300+ free agents with every team's roster; narrowing by
owner is how trades are scouted.

**Independent Test**: pick two teams and check only their players are listed; pick Free agents and
check only free agents are listed.

**Acceptance Scenarios**:

1. **Given** no team picked (the default), **Then** free agents and every other team's players are
   listed, as today.
2. **Given** **Free agents** and/or one or more teams picked, **Then** only players owned by those
   (free agents counting as one choice) are listed.
3. **Given** the Team filter, **Then** it offers Free agents and every fantasy team except the
   manager's own (whose players the picker never lists).
4. **Given** the position and team filters together, **Then** a player must match both.

---

### User Story 3 - Rank by the categories I care about (Priority: P1)

A manager building around rebounds and blocks picks REB and BLK in **Sort by**. The picker ranks
players by the xLift they add in those two categories, and shows that number.

**Why this priority**: total xLift answers "who helps most"; a build needs "who helps most where I
want help".

**Independent Test**: pick REB and BLK and check players are ordered by their REB + BLK xLift,
which is shown, and that it equals the sum of those categories in Player Analysis for the same
player and settings.

**Acceptance Scenarios**:

1. **Given** no category picked (the default), **Then** players are ranked by total xLift, as today.
2. **Given** one or more categories picked, **Then** players are ranked by their xLift summed over
   those categories, highest first (free agents first, as today), and that sum is shown with the
   categories named in its column header.
3. **Given** categories picked, **Then** the total xLift is still shown.
4. **Given** a lower-is-better category (TO), **Then** fewer turnovers count as a gain, as in xLift.

---

### Edge Cases

- **No player matches**: the picker says no players match, in place of an empty table.
- **Search plus filters**: the name search, position and team filters all apply together.
- **Paging**: the count and pages reflect the filtered list; changing a filter returns to page 1.
- **Tactical mode**: filters and sort work the same; xLift is the same league-level measure.
- **Unsupported format**: no xLift, so no category sort; filters still apply.
- **Moves**: a player moved by a hypothetical move is filtered by his owner in the scenario.
- **Swap dialog**: its own free-agent list is unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The picker MUST offer a **Position** filter with the positions G, F and C, any number
  at once; none picked means no filter.
- **FR-002**: With positions picked, a player MUST be listed only if one of his positions is
  picked.
- **FR-003**: The picker MUST offer a **Team** filter listing **Free agents** and every fantasy team
  in the league except the selected team, any number at once; none picked means no filter.
- **FR-004**: With teams picked, a player MUST be listed only if his owner in the scenario is
  picked (a free agent's owner being **Free agents**).
- **FR-005**: The picker MUST offer a **Sort by** choice of the scoring format's categories, any
  number at once; none picked means rank by total xLift.
- **FR-006**: With categories picked, players MUST be ranked by their xLift summed over those
  categories, keeping today's grouping (free agents first) and tie-break (name); the sum MUST be
  shown in a column whose header names the categories, beside the total xLift.
- **FR-007**: The per-category xLift MUST be the same breakdown as Player Analysis's for the same
  team and settings, summing to the total xLift.
- **FR-008**: Filtering, ranking and paging MUST be done by the analysis (backend); the page MUST
  NOT filter or rank rows itself.
- **FR-009**: Filters and sort MUST combine with the name search, and changing any of them MUST
  return to the first page.
- **FR-010**: With no filter and no sort picked, the picker MUST return exactly what it returns
  today.
- **FR-011**: Filter and sort choices MUST be kept while the manager makes moves; they reset when
  the league changes. A team that leaves the list (the manager's own, after a team change) is
  dropped from the Team filter.
- **FR-012**: The picker MUST have help naming the three controls in plain words, without naming
  data files, and follow the style guide.

### Key Entities

- **Picker query**: name search, positions (subset of G/F/C), owners (Free agents and/or team ids),
  sort categories (subset of the format's category keys), page.
- **Picker row**: today's row plus, when categories are picked, the summed category xLift.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With any position filter, 100% of listed players have a picked position.
- **SC-002**: With any team filter, 100% of listed players are owned by a picked owner.
- **SC-003**: With categories picked, rows are in non-increasing order of the summed value within
  each group (free agents, then rostered), and each summed value equals the Player Analysis
  breakdown's sum for those categories within 0.01.
- **SC-004**: With no filter or sort, picker results are identical to before the feature.
- **SC-005**: A filter or sort change updates the list as fast as a search does today.

## Assumptions

- **Positions are G, F and C**, as the league's player data lists them; a two-position player
  (G,F) matches either.
- **Free agents first stays.** Category sort ranks within the existing groups.
- **The picker's Team column is the owner**; the filter uses the same owner.
- **No NBA-team filter.** The clarified "team" is the fantasy owner; an NBA team filter is out of
  scope.
- **State is per session**, like the picker's search, not saved across reloads.
