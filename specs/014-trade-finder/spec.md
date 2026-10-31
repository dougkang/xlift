# Feature Specification: Trade Finder

**Feature Branch**: `014-trade-finder`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "lets work on this issue now: https://github.com/dougkang/xlift/issues/10"
(issue #10: "provide trade scenarios for similar xlift across teams — find a trade on each team that
gives a net benefit to both teams")

## Clarifications

### Session 2026-10-30

- Q: Which trade per team is shown? → A: The most balanced win-win: among trades where both teams
  gain, the one whose smaller gain is largest.
- Q: Trade sizes? → A: 1-for-1 only.
- Q: Where does it live? → A: A **Trades** section in Player Analysis, one row per team, with a
  **Try it** action that opens Impact Analysis with the swap applied.

## Overview

Teams need different things. A team that loses rebounds by a hair gains more from a rebounder than
a team that already wins rebounds easily, and the reverse holds for its guards. So a 1-for-1 trade
can raise **both** teams' expected weekly category wins at once: each side gives up a category
where it has room to spare and gets help where it's close.

The Trade Finder looks at every 1-for-1 swap between the manager's team and each other team, keeps
the ones where both teams gain, and shows the most balanced one for each team. "Gain" is the
change in a team's expected weekly category wins against the whole league, the same measure as
xLift ([Impact Analysis](../../docs/tool1-impact-analysis.md#xlift)), with both rosters changed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a win-win trade with every team (Priority: P1)

A manager opens Player Analysis and sees, for each other team, the fairest trade that helps both
sides: who they give, who they get, how much each team gains.

**Why this priority**: it's the issue's request: a ready list of trades worth proposing.

**Independent Test**: open the Trades section and check each row's trade raises both teams'
expected weekly wins, and that no other 1-for-1 swap with that team has a larger smaller-gain.

**Acceptance Scenarios**:

1. **Given** a league and team, **When** Player Analysis opens, **Then** the Trades section lists
   every other team once.
2. **Given** a team row, **Then** it shows the player given, the player received, the manager's
   gain and the other team's gain in expected weekly category wins, both above zero, signed to two
   decimals.
3. **Given** a team row, **Then** among all 1-for-1 swaps of active players with that team where
   both gain, it is the one whose smaller gain is largest (ties: larger total, then player names).
4. **Given** a team with no swap that helps both, **Then** its row says no trade helps both teams.
5. **Given** the rows, **Then** they are ordered by the smaller gain, largest first, with the
   no-trade rows last.
6. **Given** a row, **Then** it also shows the manager's gain in each category, one column per
   category, positives in bold, so the reason is visible.

---

### User Story 2 - Try a trade in Impact Analysis (Priority: P2)

The manager likes a trade and wants to see it in full: radar, H2H, breakdown.

**Why this priority**: the finder suggests; Impact Analysis is where a move is tested.

**Independent Test**: click Try it and check Impact Analysis opens with the swap as its move.

**Acceptance Scenarios**:

1. **Given** a trade row, **When** the manager clicks **Try it**, **Then** Impact Analysis opens
   for the same league, team and settings, with that swap as a move.
2. **Given** the manager already has moves in Impact Analysis, **Then** the button says it will
   replace them, and doing so leaves only the trade.

---

### Edge Cases

- **Reserve players** (IL/NA slots) aren't traded: a 1-for-1 swap of active players keeps both
  rosters legal; a reserve player contributes nothing to the week.
- **Players without a projection** (no games in the window) aren't traded.
- **Unsupported format**: the section shows the usual unsupported-format notice.
- **Moves made in Impact Analysis** don't apply: like the leaderboard, trades use rosters as they
  are, and the page already says so.
- **Evaluate for League**: trades are always for the selected team.
- **Each-category and most-categories leagues**: the measure (expected category wins) is the same.
- **Effects on other teams**: a trade also shifts other teams' expected wins slightly; only the
  two teams in the trade are reported.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For the selected team and each other team, the analysis MUST consider every 1-for-1
  swap of one active, projected player from each.
- **FR-002**: A swap's gain for a team MUST be the change in that team's expected weekly category
  wins against every other team in the league, with **both** rosters changed, using the same
  weekly lines, spreads, window and Fragility Penalty as xLift.
- **FR-003**: Per team, the trade shown MUST be the one, among swaps where both gains are above
  zero at display precision (at least +0.01), maximizing the smaller gain; ties by larger total
  gain, then by player names.
- **FR-004**: Each row MUST show the other team, the player given and received (name, NBA team,
  status), the manager's gain and the other team's gain, signed to two decimals.
- **FR-005**: Each row MUST show the manager's gain in every category, one column per category in
  the format's order, signed to one decimal, positives in bold. *(Revised 2026-10-30: first built
  as a "Why" list of the categories changing by at least 0.1.)*
- **FR-006**: Teams with no win-win swap MUST be listed with a "No trade helps both teams" note.
- **FR-007**: Rows MUST be ordered by the smaller gain, largest first; no-trade rows last, by name.
- **FR-008**: **Try it** MUST open Impact Analysis with the swap as its only move, saying so when
  it replaces existing moves.
- **FR-009**: The trades MUST be computed by the analysis (backend); the page only draws them.
- **FR-010**: The section MUST have help explaining the gains, the balanced pick and Try it in plain
  words, without naming data files, and follow the style guide.
- **FR-011**: The Trades section MUST use the same league, team, window and Fragility Penalty as
  the rest of Player Analysis.

### Key Entities

- **Trade**: the two teams, the player each gives, each team's gain, the manager's per-category
  gains.
- **Trade row**: one per other team: its best trade, or none.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every shown trade has both gains of at least +0.01 in 100% of rows.
- **SC-002**: For every team, no other win-win 1-for-1 swap of active players has a larger smaller
  gain than the one shown.
- **SC-003**: A shown trade's gain for the manager equals the change in expected weekly wins
  computed directly from the two changed rosters within 0.01.
- **SC-004**: The Trades section appears within 3 seconds of opening Player Analysis on the real
  league (18 teams).
- **SC-005**: Try it opens Impact Analysis with exactly that swap applied.

## Assumptions

- **Strategic, weekly.** Gains use xLift's league-level weekly measure; there is no tactical
  version.
- **Active players only**, 1-for-1, as clarified; multi-player trades are a later feature.
- **Other teams' changes not shown.** The trade is judged by the two teams' gains.
- **Lives in Player Analysis**, below the leaderboard, with the shared settings.
