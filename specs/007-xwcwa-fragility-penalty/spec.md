# Feature Specification: xLift in Impact Analysis and the Fragility Penalty

**Feature Branch**: `007-xwcwa-fragility-penalty`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Show xWCWA (Expected Weekly Category Wins Added) for every player in the Impact Analysis dashboard, scored for the selected team, and sort free agents by it; add a Fragility Penalty setting. Decisions: (1) xWCWA is computed from the selected team's position in the league (weekly win odds against every other team, summed over categories), with the swap baseline being the team's weakest active player (the one whose removal costs the fewest expected category wins). (2) In tactical mode, xWCWA is still shown (same league-wide weekly definition for now); the opponent's read-only roster shows xWCWA computed from the opponent team's position. (3) The player picker shows xWCWA and sorts free agents by it, highest first. (4) A "Fragility Penalty" dropdown with options None, dAB, and dAB × tag controls player availability everywhere in the analysis (strategic simulation games per period and xWCWA); dAB and the injury-tag multipliers use their default backtested parameters, which are not shown to the user. dAB is the Decay-weighted Availability Blend from the analysis/ availability report (multi-season games played vs games available, with missed seasons inferred, older seasons weighted 0.05 per season of age, window and long-run rates blended). Out of scope: tactical-specific xWCWA, surfacing dAB parameters, minutes trend multiplier."

## Clarifications

### Session 2026-10-24

- Q: Whose position is xLift scored from? → A: The selected team's. In tactical mode the
  opponent's roster uses the opponent's position.
- Q: What does tactical mode show? → A: The same league-wide weekly xLift for now.
- Q: What is the swap baseline? → A: The team's weakest active player.
- Q: What does the Fragility Penalty control? → A: Availability everywhere in the analysis. The
  options are None, Last 15, dAB and dAB × tag, with default parameters that aren't shown.
- Q: What does **None** mean? → A: No penalty for anyone outside an IL slot: they're available
  for every game. Players in an IL slot (the roster's reserve slots, IL/IL+/NA) have
  availability 0. Today's 15-game estimate is its own option, **Last 15**, which reproduces
  today's results.
- Q: What is the default? → A: **dAB × tag**.

## Overview

Impact Analysis shows what a roster move does to a team, but it doesn't say which players are
worth looking at. The free-agent picker is alphabetical, and nothing on a roster says how much
each player is worth to the team.

**xLift (expected lift: the weekly category wins a player adds)** answers that. It's developed and backtested in
the `analysis/` rankings notebook. For a team and a player, it is the change in the team's
expected category wins per week, summed over all nine categories and every other team in the
league, when the player takes the place of the team's weakest active player. A category win's
probability comes from the teams' projected per-period totals and the category's week-to-week
noise. So xLift rewards a player more where the team sits in a tight cluster of rivals, and less
where the team is already far ahead or far behind.

This feature brings xLift into the dashboard:
- next to every player on the selected team's roster;
- next to every player in the picker, with free agents sorted by it;
- in tactical mode, next to every player on the opponent's roster, scored for the opponent.

It also adds a **Fragility Penalty** setting. It chooses how player availability (how often a
player plays) is estimated, for the whole analysis:
- **None**: no penalty; every player not in an IL slot is available for every game, and
  players in an IL slot aren't available.
- **Last 15**: the existing availability estimate (games played over the most recent 15).
- **dAB**: the backtested Decay-weighted Availability Blend from the availability report.
- **dAB × tag**: dAB scaled by the player's current injury tag. This is the default.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find the free agents worth adding (Priority: P1)

As a league member looking at the waiver wire, I want free agents sorted by how many weekly
category wins they'd add to my team, so the best pickups for my team are at the top.

**Why this priority**: It's the most direct decision aid this feature offers. It turns an
alphabetical list into a ranked shortlist for the team being managed.

**Independent Test**: Open the analysis for a team and open the picker filtered to free agents.
The list is ordered by xLift, highest first, and each row shows its value. Pick the top free
agent and add them. The analysis's category picture improves at least as much as for a
lower-ranked free agent added the same way.

**Acceptance Scenarios**:

1. **Given** a selected team, **When** the picker lists free agents, **Then** they're ordered by
   xLift for that team, highest first, and each row shows its xLift.
2. **Given** two different selected teams, **When** each opens the picker, **Then** the free
   agents' xLift and order can differ, because each team's position and weakest player differ.
3. **Given** a search term, **When** the picker filters by name, **Then** the matching free
   agents keep the xLift order.
4. **Given** players rostered by other teams in the picker, **When** they're shown, **Then**
   they show xLift for the selected team too (the value of acquiring them in a swap), listed
   after free agents as today.

---

### User Story 2 - See each roster player's value to the team (Priority: P1)

As a league member, I want each player on my roster to show their xLift, so I can see who
carries the team and who is the weakest link to replace.

**Why this priority**: It's the other half of a move decision: whom to drop. It uses the same
measure as the picker, so the two can be compared directly.

**Independent Test**: Open the analysis for a team. Each active player shows xLift. The team's
weakest player shows 0, and every other active player shows a value relative to that player.

**Acceptance Scenarios**:

1. **Given** a selected team, **When** the roster is shown, **Then** each active player shows
   their xLift for the team. If every active slot is filled by a projected player, the weakest
   active player shows 0. An active player with no games is the baseline itself (an empty slot)
   and shows no value, so nobody shows 0.
   If a slot is open, the baseline is the empty slot, so each player shows their full
   contribution and none shows 0.
2. **Given** a roster player with xLift *x* and a free agent with xLift *y* > *x*, **When**
   compared, **Then** both measure value against the same baseline (the team's weakest player),
   so swapping the roster player for the free agent is expected to gain about *y* − *x*
   category wins per week.
3. **Given** a hypothetical move, **When** the analysis updates, **Then** xLift values reflect
   the roster after the move.
4. **Given** a reserve (IL/NA slot) player, **When** shown, **Then** their xLift is shown as if
   they were active, marked as not counted, since reserves don't play.

---

### User Story 3 - Choose how fragility is penalized (Priority: P2)

As a league member, I want to choose whether availability is ignored, comes from recent games
only, from the backtested multi-season model, or from that model plus current injury tags, so I
can see how much injury risk changes my picture.

**Why this priority**: Availability strongly affects value (a player who plays half the games is
worth about half as much), and the backtest showed the existing estimate is poor early in a
season. But it's a setting on top of the main features.

**Independent Test**: Switch the Fragility Penalty between its four options for the same team.
The strategic results and the xLift values change, with **Last 15** matching today's results
and **None** treating every player outside an IL slot as available for every game.

**Acceptance Scenarios**:

1. **Given** the Fragility Penalty is **None**, **When** the analysis runs, **Then** every
   player not in an IL slot has availability 1 (no penalty), so their strategic games per
   period equal the full games per period and their xLift reflects per-game value alone.
   Players in an IL slot have availability 0.
2. **Given** **Last 15**, **When** the analysis runs, **Then** availability is today's estimate,
   and the strategic results equal today's for the same inputs.
3. **Given** **dAB**, **When** the analysis runs, **Then** each player's availability is their
   dAB value, and strategic games per period and xLift use it.
4. **Given** **dAB × tag**, **When** a player is tagged injured (e.g. IL or Out), **Then** their
   availability is dAB scaled by the tag's multiplier, and an untagged player's equals dAB.
5. **Given** any option, **When** the settings are shown, **Then** no dAB or tag parameters are
   shown or editable.

---

### User Story 4 - The opponent's roster in tactical mode (Priority: P3)

As a league member in tactical mode, I want the opponent's roster to show each player's xLift
for the opponent, so I can see who their key players are.

**Why this priority**: It's useful context, but it doesn't drive a move on my own team.

**Independent Test**: Switch to tactical. The opponent's read-only roster shows xLift computed
from the opponent's position in the league. The selected team's roster and picker keep showing
xLift for the selected team.

**Acceptance Scenarios**:

1. **Given** tactical mode, **When** the opponent's roster is shown, **Then** each player shows
   xLift for the opponent team, with the opponent's weakest active player at 0.
2. **Given** tactical mode, **When** the selected team's roster and the picker are shown,
   **Then** they show xLift for the selected team, computed as in strategic mode.

### Edge Cases

- **A player with no projection** (no games in the lookback): no xLift ("–"). They sort last
  among free agents.
- **A team with an empty active slot**: there's no one to replace, so a free agent's xLift is
  the gain from filling the slot, and the weakest-player baseline is an empty slot (0).
- **A roster player whose weakest teammate has no projection**: that teammate counts as the
  weakest (they add nothing), with xLift 0.
- **Ties in xLift**: free agents with equal xLift are ordered by name.
- **Not enough history for dAB** (e.g. a rookie's first games): dAB's own fallbacks apply, as
  in the availability report.
- **IL-slot players under None**: their availability is 0, so the "as if active" xLift shown
  for them (FR-009) is 0.
- **Ratio categories**: FG% and FT% are recomputed from makes and attempts after the swap, never
  averaged.
- **TO** is lower-is-better: fewer turnovers count as a gain.

## Requirements *(mandatory)*

### Functional Requirements

**xLift**

- **FR-001**: The system MUST compute, for a team *T* and a player *i*, xLift = (*T*'s expected
  weekly category wins with *i* in place of *T*'s weakest active player) − (*T*'s expected
  weekly category wins as it stands).
- **FR-002**: For a player already active on *T*, xLift MUST be (*T*'s expected weekly category
  wins as it stands) − (*T*'s expected weekly category wins with *i* replaced by another copy of
  the weakest active player's per-period line). The weakest active player gets 0, and every
  value is against the same baseline as FR-001.
- **FR-003**: *T*'s expected weekly category wins MUST be, summed over the scoring format's
  categories and every other team *u*, the probability that *T* beats *u* in that category in a
  week. It's computed from the two teams' expected per-period totals and the category's
  week-to-week spread, as in the rankings notebook's weekly win-odds curve. The category's
  direction (TO lower-is-better) is honored.
- **FR-004**: A team's expected per-period totals MUST be the sum over its active players of
  per-game projection × availability × games per period. Ratio categories are computed from
  summed makes and attempts.
- **FR-005**: The **weakest active player** MUST be the active player whose removal (leaving the
  slot empty) costs *T* the fewest expected weekly category wins. A player without a projection
  is weakest by definition.
- **FR-006**: Each category's week-to-week spread MUST come from the analysis's own simulation:
  the median, over teams, of the standard deviation of each team's simulated per-period
  category value.
- **FR-007**: xLift MUST reflect the current scenario, including hypothetical moves, and the
  current settings (window, games per period, Fragility Penalty).
- **FR-008**: xLift MUST be computed by the core and returned by the analysis; the frontend only
  displays it.

**Display and sorting**

- **FR-009**: Each player row in the selected team's roster MUST show its xLift. Reserve
  players' values are shown but marked as not counted.
- **FR-010**: Each row in the player picker MUST show its xLift for the selected team.
  Free agents MUST be ordered by xLift, highest first, with ties by name and players without a
  projection last. Rostered players stay after free agents, also ordered by xLift.
- **FR-011**: In tactical mode, the opponent's roster MUST show xLift computed for the opponent
  team (FR-001, FR-002 with *T* = the opponent). The selected team's roster and the picker keep
  the selected team's xLift, computed as in strategic mode.
- **FR-012**: xLift MUST be shown with two decimals, signed, with a help entry that explains it
  in plain language, without file names.

**Fragility Penalty**

- **FR-013**: The analysis settings MUST include a **Fragility Penalty** control with options
  **None**, **Last 15**, **dAB** and **dAB × tag**, applied to the whole analysis: strategic
  games per period, every strategic result and xLift.
- **FR-014**: **None** MUST apply no penalty to players outside an IL slot: each such player
  with a projection has availability 1. Players in an IL slot (the roster's reserve slots:
  IL, IL+, NA) have availability 0. This applies to every team's roster in the scenario: a
  player in any team's reserve slot has availability 0. Free agents have no slot and count as
  outside one.
  **Last 15** MUST use the existing availability estimate (the most recent 15 games), so results
  with **Last 15** equal today's for the same inputs.
- **FR-015**: **dAB** MUST compute each player's availability with the Decay-weighted
  Availability Blend as specified in the availability report: a blend of a window rate and a
  multi-season long-run rate, each shrunk toward the pool rate. Every game, played or missed, is
  weighted by its season's age, and missed seasons are inferred. It uses fixed default
  parameters recorded from the backtest.
- **FR-016**: **dAB × tag** MUST multiply dAB by the multiplier of the player's current injury
  tag, using fixed default multipliers. Untagged and healthy players are unchanged.
- **FR-017**: dAB and tag parameters MUST NOT be shown or editable in the app.
- **FR-018**: In tactical mode, the Fragility Penalty MUST affect xLift only. The tactical
  matchup simulation keeps its own games-remaining rule.
- **FR-019**: The default Fragility Penalty MUST be **dAB × tag**.

### Key Entities

- **xLift value**: per (team, player). A signed number of expected weekly category wins,
  relative to the team's weakest active player.
- **Availability estimate**: per player, by Fragility Penalty option. None: 1, or 0 in an IL
  slot. Last
  15: the 15-game estimate. dAB: the backtested blend. dAB × tag: dAB times the tag multiplier.
- **dAB parameters**: fixed constants recorded from the availability backtest. They cover the
  pool rate, the season weight, the shrinkage strengths and the blend weights. Plus the tag
  multipliers.
- **Weekly category spread**: per category, used for win probabilities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For the same team, settings and data, the dashboard's xLift for every free agent
  matches the rankings notebook's team-specific value (weekly win-odds curve, weakest-player
  swap) within ±0.05 wins.
- **SC-002**: 100% of players with a projection show an xLift on the selected team's roster, in
  the picker, and on the opponent's roster in tactical mode.
- **SC-003**: The picker's free agents are in non-increasing xLift order in 100% of listings,
  including filtered and paged ones.
- **SC-004**: With Fragility Penalty **Last 15**, every strategic result is identical to the
  pre-feature results for the same inputs and seed. With **None**, every player outside an IL
  slot has availability exactly 1, and every player in one has 0.
- **SC-005**: With **dAB**, every player's availability matches the availability report's dAB
  for the same as-of date within 0.001.
- **SC-006**: The dashboard stays responsive: a cold analysis takes no more than 1.5 times its
  current time, and a cold picker listing (cache cleared) returns in under 1 second.
- **SC-007**: Adding the top-ranked free agent, swapped for the weakest player, changes the
  team's expected weekly category wins by its listed xLift within ±0.05.

## Assumptions

- **Swap baseline for roster players (FR-002):** a roster player's value is measured as "how
  much better than your weakest player", so roster and free-agent values share one baseline
  and can be compared. This is a design choice, not something the user stated.
- **Same definition in both modes:** tactical mode shows the strategic-style, league-wide weekly
  xLift for now. A tactical, matchup-specific version is out of scope.
- **Weekly spread from the analysis's simulation:** tactical mode needs per-period spreads for
  xLift, which its own simulation doesn't produce. A league-wide per-period simulation (as
  strategic runs) supplies them.
- **dAB parameters:** recorded as constants from the availability backtest on 2022-23 to
  2025-26: pool rate 0.770, season weight 0.05, long-run prior 5 games, window prior 0, blend
  weights 0.586 and 0.145, and the report's default tag multipliers (IL 0.3, O 0.6,
  Q/GTD/DTD 0.9, SUSP 0.7, NA 0). Refitting is a future concern.
- **dAB needs multi-season history**, which the database has (2022-23 onward). With less
  history, dAB still works and leans more on its priors.
- **Out of scope:** surfacing or tuning dAB parameters, a tactical-specific xLift, the minutes
  trend multiplier, and changes to the rankings notebook beyond keeping it consistent.
