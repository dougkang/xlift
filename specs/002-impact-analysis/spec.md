# Feature Specification: Impact Analysis Tool

**Feature Branch**: `002-impact-analysis`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "Impact Analysis Tool as specified by @docs/tool1-impact-analysis.md"

## Overview

Impact Analysis answers one question: **"If I make this roster move, does my team get better?"**
It shows the effect of adding, dropping, and swapping players in two ways:

- **Strategically**: the long run, against every team in the league.
- **Tactically**: this week, against the current opponent.

Results come from a Monte Carlo simulation of each player's stat distribution over their last X
games. The domain rules are in `docs/tool1-impact-analysis.md` and `docs/overview.md`. The visual
rules are in `docs/style.md`.

The tool reads leagues, rosters, schedules, and player game history through the data contract
delivered by feature 001 (`specs/001-league-data-schema`). It never writes hypothetical moves back
to that data (Constitution VII).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See where my team stands in the league (Priority: P1)

As a league member, I open Impact Analysis, pick my league and my team, and see:
- my projected record against every other team
- how my team ranks in each category
- how my team's category distributions compare with the league leader and the league average

From this I learn what my team is strong at, what it is weak at, and what it could punt.

**Why this priority**: This is the baseline every roster decision is judged against. On its own it
already answers "how good is my team, and where?".

**Independent Test**: Load the reference league. Select a team in strategic mode. Confirm that the
team name, manager, projected record against the other 17 teams, radar of category ranks,
per-category rank list, and per-category distribution curves are shown and agree with each other.

**Acceptance Scenarios**:

1. **Given** a loaded league, **When** I select a team in strategic mode, **Then** I see its name,
   its manager, and its projected matchup record (wins–losses–ties) against every other team.
2. **Given** the selected team, **When** results are shown, **Then** a radar shows the team's rank
   (1 = best) in every category of the league's scoring format. The selected team is emphasized
   and every other team is overlaid in muted colors.
3. **Given** strategic mode, **When** results are shown, **Then** a list under the radar gives the
   selected team's rank in each category.
4. **Given** strategic mode, **When** results are shown, **Then** each category has a distribution
   curve for the selected team, with the league leader's and the league average's curves overlaid
   and muted.
5. **Given** turnovers, a lower-is-better category, **When** ranks and curves are shown, **Then**
   the team with the fewest turnovers ranks first.
6. **Given** a window of X games set by the user, **When** I change X, **Then** every projection is
   recomputed from each player's last X regular-season games.
7. **Given** a different team picked in the team selector, **When** results refresh, **Then** that
   team becomes the selected team, and any hypothetical moves made so far are kept.

---

### User Story 2 - Try roster moves and see the impact (Priority: P1)

As a league member, I drop players, add free agents, or swap players with other teams, and I
immediately see how my projected record, ranks, and category distributions change. When I'm done
exploring, I reset everything back to the real rosters.

**Why this priority**: This is the purpose of the tool, so it shares P1 with US1. US1 is the
baseline; this story is the decision.

**Independent Test**: With the reference league loaded:
1. Drop a player from the selected team and confirm the player appears among free agents and the
   projections change.
2. Add a free agent into the open slot and confirm the projections change again.
3. Swap with another team's player and confirm both teams' rosters reflect the swap.
4. Reset and confirm every roster matches the loaded league exactly.

**Acceptance Scenarios**:

1. **Given** the selected team's roster, **When** I press "−" next to a player, **Then** the player
   leaves the roster, appears in the free-agent list, and all projections update.
2. **Given** the selected team has an empty active slot, **When** I press "+" next to a free agent,
   **Then** the player joins the team in an active slot and all projections update.
3. **Given** the selected team has no empty active slot, **When** I look at a free agent, **Then**
   "+" is unavailable, and I'm told a player must be dropped first.
4. **Given** a player P on another team T, **When** I press "+", **Then** I'm asked what T
   receives in return, and I can pick either option:
   - **(a)** one of my roster players. This is a 1-for-1 trade and needs no empty slot. My player
     goes to T in P's place.
   - **(b)** a free agent. T receives that free agent in P's place, which needs an empty active
     slot on my team.

   Both teams' rosters update.
5. **Given** an injured player (status O or IL) added from free agency, **When** the move
   completes, **Then** the player takes an active slot, never a reserve slot.
6. **Given** a player in a reserve slot (IL, NA) in the loaded roster, **When** results are
   computed, **Then** that player contributes nothing to the simulation and doesn't count against
   active capacity. Dropping them is allowed, and dropping them doesn't open an active slot.
7. **Given** any number of moves, **When** I press "Reset", **Then** every player returns to their
   original team or to the free-agent pool, and results match the unmodified league.
8. **Given** the player picker, **When** I type part of a name, ignoring case and accents (e.g.
   "doncic"), **Then** the list narrows to matching players not on the selected team. Each
   player's current fantasy team (or "FA") is shown.

---

### User Story 3 - Win this week's matchup (Priority: P2)

As a league member mid-week, I switch to tactical mode, pick this week's opponent, and see my
projected category record for the rest of the matchup period. Projections account for how many
games each player has left. I then try streaming free agents to flip close categories.

**Why this priority**: Tactical streaming is high-value but depends on the same views and moves as
US1–US2.

**Independent Test**: In tactical mode with an opponent chosen, compare two free agents:
- player A is slightly worse per game but has 2 games left
- player B is slightly better per game but has 1 game left

Confirm that adding A projects better than adding B in tactical mode, and that the order is
reversed in strategic mode.

**Acceptance Scenarios**:

1. **Given** tactical mode, **When** I choose an opponent, **Then** I see my projected category
   record against that opponent (e.g. 5–3–1), the probability that I win the matchup, and, for
   each category, the difference between our projected averages.
2. **Given** tactical mode, **When** the matchup period is chosen (by default the current
   Monday–Sunday week), **Then** each player's contribution is scaled by the games their NBA team
   has scheduled from today to the end of the period. Postponed and cancelled games are not
   counted.
3. **Given** tactical mode, **When** the radar and distributions are shown, **Then** only the
   opponent is overlaid (muted), not the rest of the league.
4. **Given** tactical mode, **When** I browse the player picker, **Then** each player shows how many
   games they have left in the period.
5. **Given** the same roster and settings, **When** I toggle between tactical and strategic,
   **Then** the record and ranks are recomputed for that mode. The two modes are calculated
   differently (games remaining vs. availability), not just labeled differently.

---

### Edge Cases

- **Short history**: a player with fewer than X regular-season games in all loaded seasons, such as
  a rookie, is simulated on the games available. They are marked with an asterisk everywhere they
  appear (roster, picker, swap dialog), with a footnote such as "* 3 of 15 games".
- **No history**: a player with no regular-season games at all contributes nothing to any
  category. They are flagged "* 0 of X games" and can still be added, dropped, and swapped.
- **Season boundary**: early in a season, the X-game window takes the remaining games from the
  previous season (feature 001, FR-020).
- **No games left**: in tactical mode, if no games remain in the matchup period (end of week, or
  the offseason), every player's contribution is zero, and the tool says no games remain instead
  of showing a misleading projection.
- **No opponent**: in tactical mode with no opponent chosen yet, tactical results are not shown,
  and the tool asks the user to choose one.
- **Ratio categories**: when a team's simulated attempts total zero (e.g. no free throws attempted
  in a short tactical window), the ratio category is shown as "–" for that simulation and is
  treated as a tie in that category. It is never treated as 0% or 100%.
- **Ties**: a category where both teams' simulated totals are equal is a tie for that simulation.
  A matchup where both teams win the same number of categories is a matchup tie. Ties are counted
  and reported, never dropped (Constitution I).
- **Impossible values**: simulated team totals are never negative, and made shots never exceed
  attempted shots.
- **Full roster**: adding a free agent to a team with no empty active slot is blocked, not silently
  turned into a drop.
- **Player in a reserve slot**: a reserve player (IL, NA) can't be moved into an active slot by
  any move in this tool. They can only be dropped.
- **Unsupported format**: if the league's scoring format isn't supported, the tool shows a clear
  message naming the format and shows no projections.
- **Odd team count**: strategic matchups are round-robin, so no bye handling is needed.

## Requirements *(mandatory)*

### Functional Requirements

**League, team, and settings**

- **FR-001**: Users MUST be able to choose a league from those loaded, and a selected team from that
  league's teams. Each team is shown with its name and manager.
- **FR-002**: Users MUST be able to choose the window X, the number of most recent regular-season
  games each player's distribution is fitted to. The default is 15 and the allowed range is 1–82.
- **FR-003**: Users MUST be able to switch between strategic and tactical mode. The default is
  strategic.
- **FR-004**: In tactical mode, users MUST be able to choose the opponent from the league's other
  teams, and the matchup period (start and end date). The period defaults to the current
  Monday–Sunday week.
- **FR-005**: The tool MUST show how fresh its data is: when NBA data was last loaded, and the
  date of the roster snapshot.

**Player projections**

- **FR-006**: Each player's per-game production MUST be modeled, for every raw stat the scoring
  format needs, as a distribution fitted to their last X regular-season games. The window crosses
  season boundaries when needed. Play-in, playoff, preseason, and All-Star games are never used.
- **FR-007**: A player whose window holds fewer than X games MUST be marked with an asterisk wherever
  they appear, with a footnote giving the count used (e.g. "* 3 of 15 games").
- **FR-008**: Players in reserve slots (IL, NA) in the original roster MUST contribute nothing to
  any projection.

**Team projections and scoring**

- **FR-009**: Team category totals MUST be computed per simulation by aggregating players
  according to the scoring format. Counting stats are summed. Ratio stats (FG%, FT%) are computed
  from team totals of makes and attempts, never by averaging player percentages. Lower-is-better
  categories (TO) are ranked and compared in reverse.
- **FR-010**: The scoring format MUST come from the league's settings. The first supported format
  is 9-category head-to-head (PTS, REB, AST, STL, BLK, 3PM, FG%, FT%, TO). The tool MUST NOT
  assume a fixed set of categories outside the format definition (Constitution II).
- **FR-011**: Results MUST come from a Monte Carlo simulation whose random seed and number of
  iterations can be set. The same inputs, seed, and iteration count MUST give identical results.
- **FR-012**: **Strategic mode**:
  - Every active player is given the same number of games per simulated matchup period, so
    schedule differences don't matter.
  - Each of those games is played only with probability equal to the player's availability rate:
    the games they played divided by the games their NBA team played, over the dates covered by
    their X-game window.
  - The selected team is simulated head-to-head against every other team.
- **FR-013**: **Tactical mode**: each active player's contribution covers exactly the games their
  NBA team has scheduled from today through the end of the chosen period. The selected team is
  simulated against the chosen opponent only.

**Results display**

- **FR-014**: The tool MUST prominently show the selected team's name, manager, and projected
  record.
  - **Strategic**: the record is matchups won–lost–tied against all other teams. A matchup counts
    as won when the selected team wins it in more than half the simulations, lost when it wins in
    fewer than half, and tied otherwise.
  - **Tactical**: the record is categories won–lost–tied against the opponent, using the same
    more-than-half rule for each category. The probability of winning the matchup is shown too.
- **FR-015**: The tool MUST show a radar with one axis per category, each giving a team's rank (1 =
  best) by projected average. The selected team is emphasized.
  - **Strategic**: all other teams are overlaid, muted.
  - **Tactical**: only the opponent is overlaid.
- **FR-016**: Under the radar, the tool MUST show the selected team's rank in each category
  (strategic), or the difference between the selected team's and the opponent's projected averages
  in each category (tactical). Each difference shows whether it favors the selected team.
- **FR-017**: The tool MUST show, for each category, the distribution of the selected team's
  simulated totals as a curve.
  - **Strategic**: the league leader's and the league average's curves are overlaid.
  - **Tactical**: the opponent's curve is overlaid.
  - Overlays are muted, and the selected team is emphasized.
- **FR-018**: The selected team's roster MUST be shown, with each player's slot (active or
  reserve), status (e.g. Q, O, IL, NA), NBA team, and short-history asterisk. Tactical mode also
  shows games remaining in the period.

**Moves**

- **FR-019**: Users MUST be able to drop any player from the selected team's roster. The player
  becomes a free agent.
- **FR-020**: Users MUST be able to add a free agent to the selected team only when the team has an
  empty active slot. Active slots used must never exceed the league's active roster capacity.
- **FR-021**: Users MUST be able to acquire a player P rostered on another team T through a
  one-for-one swap, giving T one of the following:
  - **(a)** a player from the selected team's roster. This is a trade and needs no empty slot.
  - **(b)** a free agent. P then needs an empty active slot on the selected team. The free agent
    joins T in an active slot.

  In both cases the incoming player takes the outgoing player's place on T, and both teams'
  rosters MUST reflect the swap. A player in a reserve slot on the selected team can be traded
  away under (a). On T they take an active slot (FR-022).
- **FR-022**: Every added or swapped player MUST take an active slot. Reserve slots MUST NOT be
  filled by any move. A player keeps a reserve slot only if they were in it in the original roster.
- **FR-023**: Users MUST be able to reset all moves in one action. All rosters then return exactly
  to the loaded state.
- **FR-024**: Moves MUST be hypothetical: they MUST NOT change the stored league data, and they
  apply league-wide for the session. Switching the selected team keeps them.
- **FR-025**: After any move, reset, or settings change, all results MUST update without further
  action from the user.

**Player picker**

- **FR-026**: The tool MUST list every NBA player not on the selected team. Each row shows the name,
  the NBA team, the current fantasy team (or "FA"), the status, and the short-history asterisk.
  Tactical mode also shows games remaining in the period.
- **FR-027**: The picker MUST filter by name as the user types. Filtering ignores case and accents
  and matches partial names.

**Presentation**

- **FR-028**: The page MUST include an "Impact Analysis" header with a one-sentence explanation of
  the tool, the mode toggle, the reset control, and the settings in FR-001 to FR-004. The page
  MUST follow `docs/style.md` (Constitution V).

### Key Entities

- **Scenario**: the hypothetical league state, made of the loaded rosters plus an ordered list of
  moves. Reset empties the move list. It is never stored back into the league data.
- **Move**: a drop, add, or swap, with the players and teams involved.
- **Analysis Settings**: league, selected team, mode, window X, and for tactical mode the opponent
  and matchup period. Also the simulation seed and iteration count.
- **Player Projection**: for one player, per-stat per-game distributions; games found vs. games
  requested (for the asterisk); the availability rate (strategic); and games remaining in the
  period (tactical).
- **Team Projection**: for one team under the scenario and settings, the simulated distribution of
  each category total, the category averages, and the category ranks.
- **Matchup Projection**: for two teams, the probability that each category is won, lost, or tied,
  and the probability that the matchup is won, lost, or tied.
- **Projected Record**: wins–losses–ties of matchups (strategic) or of categories (tactical) for the
  selected team.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After any move, reset, mode change, or settings change, updated results appear in
  under 2 seconds for an 18-team league at the default settings.
- **SC-002**: Running the same scenario with the same settings and seed twice gives identical
  records, ranks, probabilities, and curves.
- **SC-003**: At the default iteration count, re-running with 5 different seeds changes no
  matchup or category win probability by more than 3 percentage points.
- **SC-004**: In the docs' streaming example, the player with more games remaining ranks higher in
  tactical mode, and the better per-game player ranks higher in strategic mode, 100% of the time.
  The example is a slightly worse player with 2 games left vs. a slightly better player with 1 game
  left.
- **SC-005**: In a constructed league where one team leads every category, that team's strategic
  record is all wins, and its rank is 1 in every category, including TO (fewest).
- **SC-006**: A team's simulated FG% and FT% always equal its total makes divided by its total
  attempts. This is checked on every simulation in automated tests.
- **SC-007**: A user can find a free agent by name, add them, and read the change in their
  projected record in under 30 seconds.
- **SC-008**: Every player with fewer than X games in their window shows the asterisk and footnote
  everywhere they appear: 100% coverage in the roster, picker, and swap views.
- **SC-009**: After any sequence of moves, one reset restores rosters identical to the loaded
  league, and the stored league data is unchanged.

## Assumptions

- **Data**: league, roster, status, schedule, and game-history data come from feature 001's read
  interface. Data loading is out of scope for this feature.
- **Strategic games per period**: every player gets 3 games per simulated matchup period. This
  removes schedule effects while keeping week-like variance. Only relative results matter, so the
  exact value changes spread, not ranks.
- **Availability window**: the availability rate is measured over the dates spanned by the
  player's X-game window. A player with no games has no rate and contributes nothing.
- **Games remaining**: in tactical mode, games still scheduled today count; games already final
  today don't. Stats already scored in the current matchup are out of scope, as agreed in feature
  001.
- **Statuses**: injury statuses (Q, O, DTD) are shown but not modeled in tactical mode. The user
  decides whether to drop or stream around them. Reserve slots are the only modeled
  unavailability.
- **Distributions**: per-game stats use a normal distribution by default (Constitution III). The
  stats are modeled jointly (a multivariate normal), so related stats such as makes and attempts
  move together. Points are derived from the shooting stats, so they always agree. This was
  decided during planning; see research R1.
- **Daily lineups**: daily lineup limits and positional eligibility aren't modeled. Every active
  player's games count.
- **Swaps**: swaps are one-for-one. Multi-player trades are out of scope.
- **Defaults**: 15-game window (the docs' example), strategic mode, and an iteration count chosen in
  planning to meet SC-001 and SC-003.
- **Persistence**: moves last for the current browser session. Reloading the page or pressing Reset
  starts again from the loaded rosters.
- **Users**: a single local user, with no sign-in.
- **Out of scope**: the docs' "Next Steps": fit-error propagation, time-based windows, and decayed
  weighting of past seasons. The constitution requires the model to leave room for them.
