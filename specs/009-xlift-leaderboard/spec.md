# Feature Specification: xLift Leaderboard, the Start of Player Analysis

**Feature Branch**: `009-xlift-leaderboard`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "implementation of the RGP leaderboard graph as the start of a Player Analysis and Comparison tool"

## Clarifications

### Session 2026-10-24

- Q: Whose position is xLift scored from? → A: Both, with an **Evaluate for** toggle: **Your
  team** (the default, as in Impact Analysis) or **League** (averaged over every team except the
  player's own).

## Overview

Impact Analysis answers "what does this move do to my team?", but only after the manager has a
player in mind. The picker lists players by xLift, one number per row, so it shows who is worth
the most but not *why*: which categories a player helps, and which they hurt.

The rankings notebook in `analysis/` answers that with its **xLift leaderboard** (called the RGP
leaderboard in the notebook's code, from xLift's earlier name). The leaderboard has one
horizontal bar per player, split into the category wins the player adds in each category, with a
tick at the player's net xLift. At a glance it shows who the best adds are and what kind of
player each one is, e.g. a big-man profile (rebounds and blocks, giving back FT%) or a
shooter's (threes and FT%).

This feature brings that leaderboard into the app as the first view of a new tool, **Player
Analysis** ([Tool 2](../../docs/tool2-player-comparison.md)). The tool will grow to cover
player discovery and comparison. This first step is the leaderboard alone.

xLift is the app's existing measure (see [Impact Analysis](../../docs/tool1-impact-analysis.md#xlift)):
expected extra category wins per week, summed over every opponent in the league, when the player
takes the place of the team's weakest active player. This feature uses the same definition and
the same numbers. It only adds a new way to see them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the best free agents for my team, and why (Priority: P1)

A manager opens Player Analysis, picks their league and team, and sees the free agents ranked by
xLift for that team. Each player's bar shows how much of their value comes from each category, so
the manager can tell a balanced add from one that wins three categories and gives back two.

**Why this priority**: it's the view the user asked for and the core of the tool. On its own it
turns the waiver wire into a ranked, explained shortlist.

**Independent Test**: open Player Analysis for a team and check that the free agents are listed
by xLift, highest first, each with a bar split by category and a tick at their net xLift, and that
the numbers match the Impact Analysis picker for the same team and settings.

**Acceptance Scenarios**:

1. **Given** a league and team, **When** Player Analysis opens, **Then** it shows the top 25 free
   agents by xLift for that team, highest first, one row per player.
2. **Given** a player's row, **Then** the bar is split into one segment per category of the
   league's scoring format. Each segment's length is the category wins the player adds in that
   category, and the segments sum to the player's net xLift.
3. **Given** a player who costs the team in a category (e.g. a negative FG% contribution), **Then**
   that segment is drawn on the other side of zero, and the tick marks the net xLift.
4. **Given** a row, **Then** it shows the player's name, who they belong to ("Free agent" or the
   fantasy team's name), and their net xLift, signed, to two decimals.
5. **Given** a segment, **When** the manager hovers it, **Then** they see the player, the category,
   and the category wins added to two decimals.
6. **Given** the same league, team and settings, **Then** each player's net xLift equals the value
   the Impact Analysis picker shows for that player.

---

### User Story 2 - Widen or narrow the list (Priority: P2)

The manager can include players on other teams (trade targets), show more or fewer rows, and hide
players whose projection rests on too few games.

**Why this priority**: free agents are the most common decision, but trades and depth (a top 50)
are the next questions. These are the notebook's leaderboard controls that still apply in the app.

**Independent Test**: switch the pool to all players, change the number shown and the minimum
games, and check that the list changes as described.

**Acceptance Scenarios**:

1. **Given** the **Pool** is **Free agents** (the default), **Then** only free agents are listed.
   **Given** **All players**, **Then** players on other fantasy teams are listed too, ranked
   together with free agents by the same xLift, each labeled with their fantasy team.
2. **Given** **Show top** is set to *n* (10 to 50 in steps of 5, default 25), **Then** exactly the
   top *n* players are shown, or all eligible players if fewer.
3. **Given** **Min games** is set to *m* (1 to 15, default 5), **Then** players whose projection is
   based on fewer than *m* games are not listed.
4. **Given** a player is shown whose projection uses fewer games than the window, **Then** they
   carry the app's usual asterisk and footnote (e.g. "* 3 of 82 games").
5. **Given** **Evaluate for** is **Your team** (the default), **Then** values are scored for the
   selected team. **Given** **League**, **Then** each player's values are the average over every
   team except their own, the ranking follows that average, and changing the selected team
   doesn't change it.

---

### User Story 3 - Move between the two tools (Priority: P2)

The manager can switch between Impact Analysis and Player Analysis, keeping the same league,
team and settings.

**Why this priority**: the leaderboard finds a player, and Impact Analysis tests the move. The two
are used together, so getting from one to the other must be easy.

**Independent Test**: from Impact Analysis, go to Player Analysis and back, and check that the
league, team, window and Fragility Penalty are kept.

**Acceptance Scenarios**:

1. **Given** either tool, **Then** a plain-text navigation names both tools and marks the current
   one.
2. **Given** a league, team, window and Fragility Penalty chosen in one tool, **When** the manager
   switches tools, **Then** the other tool opens with the same choices.
3. **Given** hypothetical moves in Impact Analysis, **When** the manager opens Player Analysis,
   **Then** the leaderboard uses the league as it is, without those moves, and says so.

---

### Edge Cases

- **Negative categories**: a player can add wins in some categories and cost them in others (FG%
  and FT% from a high-volume, low-percentage shooter, or TO). Negative segments extend left of
  zero, positive ones right, and the tick sits at the net, which can be inside the bar or past it.
- **Negative net xLift**: a player worse than the team's weakest active player has a net below
  zero. They are still ranked by value (last), and the tick is left of zero.
- **No projection** (no games in the window): no xLift, so the player isn't listed.
- **Ties**: players with equal net xLift are ordered by name.
- **The selected team's own players**: under **Your team** they are the team being scored, so they
  never appear, even with **All players**. Under **League** no single team is being scored, so with
  **All players** they appear like any other rostered player, scored for the other teams.
- **An empty active slot on the selected team**: as in Impact Analysis, the baseline is the empty
  slot, so each player's xLift is the full gain from filling it.
- **Fewer eligible players than Show top**: all of them are shown, and the list is shorter.
- **No eligible players** (e.g. Min games excludes everyone): the leaderboard says no players match
  the filters, instead of an empty chart.
- **Lower-is-better categories** (TO): fewer turnovers count as a gain, so a low-turnover player's
  TO segment is positive.

## Requirements *(mandatory)*

### Functional Requirements

**The tool**

- **FR-001**: The app MUST have a second tool, **Player Analysis**, on its own page with its own
  masthead and a one-line explanation of what it's for.
- **FR-002**: Both tools MUST show a plain-text navigation naming Impact Analysis and Player
  Analysis, with the current tool marked by weight or underline.
- **FR-003**: Player Analysis MUST let the manager choose the league, the team, the window and the
  Fragility Penalty, with the same options and defaults as Impact Analysis.
- **FR-004**: The league, team, window and Fragility Penalty MUST carry over when switching between
  the tools.
- **FR-005**: The leaderboard MUST use the league's rosters as imported. Hypothetical moves made in
  Impact Analysis MUST NOT apply. When moves exist, Player Analysis MUST say the leaderboard
  ignores them.

**xLift**

- **FR-006**: xLift MUST be computed exactly as in Impact Analysis: the weekly win-odds measure,
  the selected team's weakest active player as the swap baseline, and the chosen window and
  Fragility Penalty. It MUST come from the same shared computation, not a copy.
- **FR-007**: Each player's xLift MUST be broken down by category: the change in the team's
  expected weekly category wins in that category, summed over every other team. The category
  values MUST sum to the net xLift.
- **FR-008**: An **Evaluate for** control MUST choose whose position xLift is scored from:
  - **Your team** (the default): the selected team's position, as in Impact Analysis.
  - **League**: each player is scored for every team except their own, each team with its own
    baseline (its weakest active player, or an empty slot when it has an open active slot or an
    active player with no games, as in Impact Analysis), and the per-category values are
    averaged over those teams. This is a position-neutral value. Its net is the average of the per-team nets, so the
    categories still sum to it.
- **FR-009**: xLift MUST be computed by the analysis (backend) and only drawn by the frontend. The
  frontend MUST NOT compute xLift, its breakdown or the ranking.

**The leaderboard**

- **FR-010**: The leaderboard MUST show one row per eligible player, ordered by net xLift, highest
  first, ties by name.
- **FR-011**: Each row MUST show a horizontal bar of the player's per-category values, stacked in
  the scoring format's category order: positive values right of zero, negative values left.
- **FR-012**: Each row MUST show a tick at the player's net xLift.
- **FR-013**: Each row MUST be labeled with the player's name, their fantasy team or "Free agent",
  and their net xLift, signed, to two decimals.
- **FR-014**: Each category MUST have one color, from the style guide's qualitative palette for
  unrelated categories, the same on every row, with a legend naming the categories.
- **FR-015**: Hovering a segment MUST show the player, the category and the value to two decimals.
- **FR-016**: A **Pool** control MUST offer **Free agents** (default) and **All players** (free
  agents plus rostered players). Under **Your team**, the selected team's players are never
  listed. Under **League**, every rostered player is eligible. *(Amended 2026-10-29: Pool is a
  dropdown that also offers each fantasy team, listing only that team's players; under **Your
  team** the selected team isn't offered.)*
- **FR-017**: A **Show top** control MUST set how many players are shown: 10 to 50 in steps of 5,
  default 25.
- **FR-018**: A **Min games** control MUST hide players whose projection is based on fewer games:
  1 to 15, default 5.
- **FR-019**: Players with fewer games than the window MUST show the app's asterisk and games
  footnote, as in Impact Analysis.
- **FR-020**: When no player matches the filters, the leaderboard MUST say so in place of the chart.
- **FR-021**: The leaderboard MUST have help explaining the bar, the segments, the tick and the
  controls in plain words, within the help length limit and without naming files.
- **FR-022**: The page MUST follow the style guide (fonts, chrome colors, lines, controls), and the
  stacked-bar leaderboard MUST be added to the style guide as a new chart idiom.

### Key Entities

- **Leaderboard entry**: one per eligible player: the player, who they belong to (fantasy team or
  free agent), the games their projection is based on, the net xLift, and the per-category xLift.
- **Leaderboard request**: league, team, window, Fragility Penalty, evaluate for, pool, show top,
  min games.
- **Category**: from the league's scoring format: its label, its order and its color.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Under **Your team**, for the same league, team and settings, every listed player's
  net xLift equals the Impact Analysis picker's xLift for that player at display precision (two
  decimals).
- **SC-002**: For every listed player, the per-category values sum to the net xLift within 0.01.
- **SC-003**: Under the **Last 15** Fragility Penalty (the only option where the notebook's lines
  and weekly spreads match the app's), for the same league, team and window, the values match the
  rankings notebook's leaderboard (weekly win odds, weakest-player swap) within ±0.05:
  - **Your team**, for every free agent, against the notebook's *Your team*;
  - **League**, for every free agent, against its *League (position-neutral)*, averaged over the
    teams without an open active slot. Where a team has an open slot, the app scores it as an
    empty slot (as Impact Analysis does), and the notebook doesn't.
- **SC-004**: The rows are in non-increasing net xLift order in 100% of views, for every pool, show
  top and min games setting.
- **SC-005**: The leaderboard appears within 3 seconds of opening the tool or changing a setting on
  the real league, cold, under either **Evaluate for** option.
- **SC-006**: Each category's segment is distinguishable without hovering. Adjacent segments in
  the stacking order never share a color, and every segment at least 0.10 wins long is wide
  enough to see (at least 4px at the default width).
- **SC-007**: Impact Analysis's numbers and behavior are unchanged, apart from the navigation.

## Assumptions

- **The leaderboard graph is the notebook's section 4 chart.** The notebook's table, its flat-SGP
  comparison, the rank-vs-rank scatter and "your team's ladder" are out of scope here; they may be
  added to the tool later.
- **No comparison yet.** Side-by-side comparison of chosen players, the "subvert correlated stats"
  idea and other discovery views are later features.
- **The app's xLift settings, not the notebook's.** Impact Analysis fixed the rank curve (weekly
  win odds) and the swap baseline (weakest active player) in feature 007. The notebook's *Rank
  curve* and *Swap out* toggles aren't brought over.
- **Strategic only.** xLift is a league-wide weekly measure, so the tool has no tactical mode.
- **No moves.** The tool doesn't make or carry roster moves. Testing a move stays in Impact
  Analysis; the tools are independent (Constitution VII).
- **No click-through yet.** Clicking a player doesn't open Impact Analysis with that move. This is
  a natural next step.
- **Name.** The tool is **Player Analysis**, Tool 2 in the docs. Its doc is
  `docs/tool2-player-comparison.md`, and `docs/overview.md`'s tool list links it under that
  name.
- **Category colors.** The qualitative palette has nine colors, enough for 9cat. A format with
  more categories would need a style guide amendment.
