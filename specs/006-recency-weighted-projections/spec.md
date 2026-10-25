# Feature Specification: Recency-Weighted Player Projections

**Feature Branch**: `006-recency-weighted-projections`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Recency-weighted player projections. Change how Impact Analysis fits each player's per-game stat distribution so recent games count more and older seasons count less, and keep the per-game mean shrinkage toward a typical player that was added after feature 005 (currently undocumented in a spec). Scope: (1) the per-game fit uses up to the user's "Last X games" (now a maximum lookback, default 82) with each game weighted 0.5^(games ago / 40) times 0.25 per season of age; weighted mean and covariance, with the effective sample size replacing the game count in covariance shrinkage, fit error and mean shrinkage; (2) empirical-Bayes mean shrinkage toward the pool of players with a game in the past year (counting stats by sampling error, percentages beta-binomial), except blocks which stay unshrunk; (3) availability stays the existing short-window estimate over the most recent 15 games (dAB is out of scope); (4) the short-history footnote and help text reflect the new meaning of the window. Evidence: analysis backtests (6,847 player-cutoffs, 3 seasons, leave-one-season-out) show the weighted fit reduces next-15/30/60-game per-game stat error by 25–30% vs the 15-game equal-weight window; shrinkage helps further (stars' points bias +1.0 → +0.2) except blocks. Out of scope: dAB availability model, minutes trend multiplier, roles."

## Overview

Today every player's projection is fit to their **last 15 games, each counted equally**. That
window has two problems, both measured in the `analysis/` backtests:

- **It's noisy.** Fifteen games is a small sample, so a hot or cold stretch moves a player's
  projection a lot.
- **It treats all 15 games as equally current.** Last night's game counts the same as a game
  from five months ago. Early in a season, most of the window is last season's games.

This feature changes the fit in two ways:

1. **Recency weighting.** The fit looks back over up to the user's *Last X games* (now a
   maximum, default 82). Each game counts less the further back it is, and less again for
   each season it's older. A long, gently decayed history is both steadier than 15 games and
   quicker to follow a real change in role.
2. **Mean shrinkage toward a typical player.** This was added to the code after feature 005
   without a spec; this feature documents it and adjusts it. Each player's per-game averages are
   pulled toward a typical player's by how noisy they are: hard for a rookie with two games,
   barely for a veteran. **Blocks are exempt**, since a center's block rate is skill, not
   noise.

**Availability doesn't change.** It stays the existing estimate over the most recent 15 games.
The backtested availability model (dAB) is a separate feature.

The Monte Carlo simulation doesn't change: it draws from each player's fitted distribution as
before. Only the fit is different.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Projections follow current form without overreacting (Priority: P1)

As a league member weighing a roster move, I want each player's projection to reflect how
they're playing now, so a player whose role has collapsed is projected lower, while one bad
game barely moves an established player.

**Why this priority**: This is the feature's value. The current 15-game window both lags real
changes and overreacts to short streaks, which misranks the players a move decision is about.

**Independent Test**: Run Impact Analysis for a team with an established player who has two
poor recent games and a long strong history. The player's projected per-game stats sit between
the two, much closer to the history. Compare a player with the same recent games but a short
history: their projection moves further.

**Acceptance Scenarios**:

1. **Given** a player with 82+ games whose last 2 games are far below their average, **When**
   the analysis runs, **Then** their projected per-game stats are below their 82-game equal
   average but well above the 2-game average.
2. **Given** two otherwise identical stretches of games, one from this season and one from last
   season, **When** the analysis runs, **Then** this season's stretch moves the projection more.
3. **Given** a player who missed a whole season, **When** the analysis runs, **Then** games from
   before the missed season count less than they would without the gap.

---

### User Story 2 - Small samples are pulled toward a typical player (Priority: P1)

As a league member, I want a rookie's two-game line or a reserve's 10-for-10 free throws to be
treated as the small samples they are, so a lucky start doesn't make a player look like a
star.

**Why this priority**: Without it, the weighted fit's smaller effective samples for rookies and
returning players would produce extreme projections. Shrinkage also measurably improves stars'
projections (their recent averages tend to fade).

**Independent Test**: Compare a rookie with 2 games against a veteran with a long history and
the same per-game averages. The rookie's projection is pulled much more toward a typical
player. A player's blocks are not pulled at all.

**Acceptance Scenarios**:

1. **Given** a player with few effective games, **When** the analysis runs, **Then** their
   per-game averages are pulled toward the typical player's more than a player with many.
2. **Given** a player shooting an extreme free-throw percentage on few attempts, **When** the
   analysis runs, **Then** their projected percentage is pulled toward the league rate, and a
   player with many attempts is pulled less.
3. **Given** any player, **When** the analysis runs, **Then** their projected blocks equal their
   weighted average, unshrunk.
4. **Given** too few players with history to estimate a typical player (fewer than 30 with 5+
   games), **When** the analysis runs, **Then** no shrinkage is applied.

---

### User Story 3 - The games setting means "how far back" (Priority: P2)

As a league member, I want the *Last X games* setting to read as the most games a projection
may draw on, defaulting to a full season, with short histories still marked.

**Why this priority**: The setting's meaning changes. The page must say so, or users will think
projections still use the last X games equally.

**Independent Test**: Open the analysis with default settings and read the setting's value and
help text. Set it lower and confirm projections draw on fewer games. Find a player with a short
history and confirm the footnote.

**Acceptance Scenarios**:

1. **Given** default settings, **When** the page loads, **Then** the setting shows 82.
2. **Given** the setting's help, **When** it's opened, **Then** it explains that recent games
   count more and that small samples are pulled toward a typical player.
3. **Given** a player with fewer games than the setting, **When** they appear, **Then** they're
   marked with the existing short-history footnote ("* N of X games").

---

### User Story 4 - Availability is unchanged (Priority: P3)

As a league member, I want how often a player is expected to play to stay exactly as it is,
since only the per-game fit is changing.

**Why this priority**: It keeps this feature's effect isolated and its results comparable.

**Independent Test**: For the same inputs, compare each player's availability before and after
this feature: identical.

**Acceptance Scenarios**:

1. **Given** any player and the same data and as-of date, **When** the analysis runs with the
   new default lookback, **Then** their availability equals what it was with the old 15-game
   window.

### Edge Cases

- **No games in the lookback:** no projection, as today; the player contributes nothing and is
  footnoted.
- **One game:** the fit uses that game; its covariance relies on the prior, as today.
- **A setting of 1 game:** the fit uses only the most recent game; recency weighting has no
  effect.
- **A game from a season before the as-of date's season with no season in between:** it
  counts one season of age. A missed season in between adds a season of age.
- **Zero attempts in a percentage:** shrinkage falls back to the league rate for that player.
- **Players without history in the past year:** they're still projected, but don't inform the
  typical player.

## Requirements *(mandatory)*

### Functional Requirements

**Recency-weighted fit**

- **FR-001**: Each player's per-game fit MUST use up to their most recent *X* games played, where
  *X* is the *Last X games* setting (range 1–82, default 82).
- **FR-002**: Each game MUST be weighted by 0.5^(*j* / 40) × 0.25^*a*, where *j* is how many
  games ago it was (0 for the most recent) and *a* is its season's age: the number of seasons
  between its season and the as-of date's season.
- **FR-003**: The fit's mean and covariance MUST be the weighted mean and weighted covariance of
  the per-game stat vectors. With equal weights they equal the current unweighted ones.
- **FR-004**: The fit MUST compute an **effective number of games**, (Σ*w*)² ÷ Σ*w*², and use it
  in place of the game count wherever the fit uses a sample size: the covariance shrinkage, the
  fit error, and the mean shrinkage.
- **FR-005**: The fit's distribution family (joint normal), the derived PTS and the simulation
  MUST NOT change.

**Mean shrinkage**

- **FR-006**: Each player's per-game means MUST be shrunk toward a typical player estimated from
  every player with a game in the year before the as-of date and at least 5 games in the
  lookback, fit the same way.
- **FR-007**: A counting stat MUST be shrunk by its share of sampling error: *m* + *w*(*x̄* − *m*),
  with *w* = *τ*² ÷ (*τ*² + *se*²), where *m* is the typical player's mean, *τ*² the spread between
  players that isn't sampling error, and *se* the player's fit error.
- **FR-008**: A percentage MUST be shrunk toward the league rate in proportion to attempts:
  (makes + *κ* × rate) ÷ (attempts + *κ*), with makes and attempts counted over the effective
  games and *κ* estimated from the pool.
- **FR-009**: Blocks MUST NOT be shrunk.
- **FR-010**: When fewer than 30 players qualify for the pool, no shrinkage MUST be applied.
- **FR-011**: Subset constraints (3PM ≤ FGM) MUST hold after shrinkage.
- **FR-012**: The typical player MUST NOT depend on which players a request asks for: projections
  built in separate requests with the same settings and data share it.

**Availability and display**

- **FR-013**: Availability MUST be computed exactly as before, over the player's most recent 15
  games played, whatever the *Last X games* setting.
- **FR-014**: The short-history footnote MUST keep its current rule and wording: shown when a
  player has fewer games than the setting.
- **FR-015**: The *Last X games* help MUST say that it's the most games a projection draws on,
  that recent games count more, and that small samples are pulled toward a typical player.
- **FR-016**: The domain docs and the model research notes MUST describe the weighting, the
  shrinkage and the blocks exemption, with the backtest evidence.

### Key Entities

- **Player projection**: a player's fitted per-game distribution (mean, covariance, fit error),
  now also with its effective number of games.
- **Typical player (mean prior)**: per-stat means and between-player spread, and per-percentage
  league rate and strength, estimated from the pool. Records which stats are exempt.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the `analysis/` backtest (early- and mid-season cutoffs over three seasons),
  projected per-game counting stats have at least 20% lower mean squared error over the next 15
  games than the current 15-game equal-weight window.
- **SC-002**: The same holds over the next 30 and 60 games (early-season cutoffs).
- **SC-003**: For players projected at 20+ points, the average error in projected points over
  the next 15 games is within ±0.5 points a game (it's about +1 before shrinkage).
- **SC-004**: Every player's availability is identical before and after this feature for the
  same data, as-of date and settings.
- **SC-005**: Results are reproducible: the same inputs and seed give identical results.
- **SC-006**: An analysis returns about as fast as today: a cold analysis of the real league
  takes no more than 1.5 times its current time.
- **SC-007**: On the same backtest, projected FG% and FT% have at least 10% lower error than the
  weighted fit without shrinkage, over the next 15 games. Error is the squared difference from
  the player's actual percentage, weighted by the attempts they then took.

## Assumptions

- **Fixed weighting:** the 40-game half-life and the 0.25 season weight are fixed, not user
  settings. Across 15-, 30- and 60-game horizons, the backtest's best settings stay within about a
  point of these.
- **Evidence base:** the backtests use the loaded seasons 2022-23 to 2025-26, leave one season
  out, and are reproduced in the `analysis/` notebooks. They measure point forecasts of per-game
  stats; the simulation's spread isn't separately validated here. Measured results:
  - **Weighted fit vs. the 15-game window:** counting stats 25–30% lower error over the next
    15, 30 and 60 games; FG% 25% and FT% 33% lower over the next 15.
  - **Shrinkage on top of the weighted fit, counting stats:** +1–3% over 15 games, up to
    +4–9% over 60 (steals, threes, turnovers). It removes most of stars' points bias (about +1
    point a game to +0.1–0.2). Blocks get worse when shrunk at every horizon (−2% to −3.5%),
    hence the exemption.
  - **Shrinkage on top of the weighted fit, percentages** (20,569 player-cutoffs,
    attempt-weighted): FG% 11% and FT% 17% lower error over the next 15 games; 20% and 32%
    for low-volume shooters, 3% for high-volume ones; FT% up to 29% over 60 games. Shrunk
    projections match later shooting across the range (players at 90%+ FT projected .856,
    shot .859).
- **Known limitation, FG% at the extremes:** shrinkage pulls the highest field-goal percentages
  (60%+, mostly centers) slightly too far (projected .607, actual .629) and the lowest slightly
  too little (.401 vs. .418). As with blocks, a center's efficiency is partly skill. A
  position- or role-aware prior is a possible follow-up; it isn't in this feature.
- **Season of a game:** a game's season is its NBA season label; season age is the difference in
  the seasons' starting years.
- **Default change:** the default lookback moves from 15 to 82 for everyone. The page keeps its
  settings and moves for the browser tab (session storage), so the stored state's key moves to
  a new version: a tab saved under the old default starts fresh at 82 rather than restoring 15.
- **Footnote basis:** the footnote keeps counting games played rather than effective games, so a
  player with a long but mostly old history isn't footnoted. Showing effective games is a
  possible follow-up.
- **Out of scope:** the dAB availability model, the minutes trend multiplier, and minutes roles.
  They stay in the `analysis/` notebooks.
