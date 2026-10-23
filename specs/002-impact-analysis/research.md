# Phase 0 Research: Impact Analysis Tool

Measurements below are from prototypes run on 2026-10-23 against the real database built in
feature 001: 18-team `ccsv-2026` league, 2025-26 and 2026-27 regular seasons, NumPy 2.5,
Python 3.14.

## R1. Player model: one joint normal draw per player, not independent normals per stat

**Decision**:
- **Fit**: for each player, fit a multivariate normal over the per-game vector of raw stats the
  scoring format needs. For 9cat that is FGM, FGA, FG3M, FTM, FTA, REB, AST, STL, BLK, TOV. The
  fit uses the player's last X regular-season games.
- **PTS is derived, not drawn**: PTS = 2·FGM + FG3M + FTM, which is an exact box-score identity.
  This keeps PTS consistent with the shooting stats it comes from.
- **Covariance shrinkage**: Σ = (1 − λ)·S + λ·D, where:
  - S is the sample covariance;
  - D = diag(max(μⱼ, 0.25)), a Poisson-like prior variance;
  - λ = k / (n − 1 + k), with k = 5 pseudo-games and n = games in the window.

  Thin histories lean on the prior; long histories use their own covariance. Σ is always positive
  definite, so a Cholesky factor always exists (a 1e-9 jitter guards round-off).
- **Players with n = 0** have no fit. They contribute nothing and are flagged "0 of X".
- **Fit error is kept but unused**: each projection also stores n and the standard error of the
  mean (Σ / n). Constitution III requires leaving room for the docs' "propagate fit error" next
  step, and a later feature can use these without a redesign.

**Rationale**:
- FG% and FT% depend on makes and attempts moving together. Independent normals for FGM and FGA
  make their ratio far too noisy, which misranks the percentage categories. That is the
  aggregation risk Constitution I exists for.
- A multivariate normal is still "a normal distribution", which satisfies the docs and
  Constitution III.

**Spec change**: the spec's assumption "correlations between stats aren't modeled in this version"
is replaced by "per-game stats are modeled jointly (a multivariate normal), so related stats such
as makes and attempts move together". The spec was updated with this plan.

**Alternatives considered**:
- **Independent normals per stat**: rejected because ratio categories become badly calibrated.
- **Bootstrap resampling of actual games**: preserves every correlation exactly, but it isn't a
  fitted distribution (Constitution III), it gives no fit-error handle, and with X = 3 it can only
  ever produce 3 distinct game lines.

## R2. Simulation mechanics

**Decision**:
- **Sampling a player's period total**: the sum of k i.i.d. game vectors is
  MVN(k·μ, k·Σ). Each simulation draws a player's period total directly as
  k·μ + √k · (L·z), where L is the Cholesky factor. There is no per-game loop.
  - **Strategic**: k ~ Binomial(G = 3, p), where p is the availability rate (R4).
  - **Tactical**: k = the games scheduled in the period (R5), fixed for every simulation.
- **Validity rules are applied to team totals, not to each player**. Raw player draws are summed
  into team totals; then each team total is:
  - floored at 0;
  - rounded to an integer, so ties happen as they do in real box scores;
  - kept consistent: FGM ≤ FGA, FG3M ≤ FGM, FTM ≤ FTA.

  PTS is derived after that.
- **Iterations**: 10,000 by default, settable from 1,000 to 50,000.
- **Random streams**: each player's draws come from `default_rng([seed, player_id, mode])`. The
  default seed is a fixed constant (`20261023`), and the user can change it.
  - Every player's draws are identical before and after a move, except for the players the move
    touched. The before/after difference therefore reflects the move, not simulation noise
    (common random numbers).
  - The same inputs and seed give identical output (SC-002).

**Measured**:
- **Clipping bias**: per-player clipping and rounding inflates a low-volume stat (0.3 BLK per game
  over 3 games) by 8.6% (0.977 against 0.900). At the team level the bias is gone: 9.006 against
  a target of 9.0 for 10 such players. Hence the rule above. A planned test asserts that simulated
  team means stay within 1% of Σ k·μ for counting stats.
- **Speed**: strategic mode, 18 teams, about 10 active players each, 10,000 iterations: **0.15 s**.
  Fetching windows from SQLite: 0.05 s.
- **Stability**: across 5 seeds, the largest change in any of the selected team's 170 win
  probabilities (17 matchups and 153 category probabilities) was **2.0 percentage points**,
  within SC-003's 3. The planned SC-003 test covers every team and both modes. With about 3,000
  probabilities the widest spread will be somewhat larger, and 10,000 iterations gives the margin
  for it.

**Alternatives considered**:
- **5,000 iterations**: the expected widest spread across 5 seeds rises to about 2.8–3.5 points,
  which is too close to the SC-003 limit.
- **A per-game simulation loop**: about 3× slower, with identical results under the normal model.

## R3. Category values, comparisons, ties

**Decision**: the scoring format turns team stat totals into category values and outcomes
(contracts/scoring-format.md).

- **Additive category**: the team total.
- **Ratio category**: Σ makes / Σ attempts, computed per simulation. It is NaN when attempts are
  0, and a NaN on either side makes that category a tie in that simulation (spec edge case).
- **Direction**: a lower-is-better category (TO) is compared and ranked in reverse.
- **Category outcome**: +1, 0 or −1 per simulation.
- **Matchup outcome**: the sign of (categories won − categories lost). Equal counts are a matchup
  tie.
- **Probabilities**: P(win), P(tie) and P(loss) are fractions of the simulations, reported for each
  category and for the matchup.
- **Records** (spec FR-014):
  - An item counts as a win when P(win) > 0.5, a loss when P(loss) > 0.5, and a tie otherwise.
  - The "items" are matchups against each opponent in strategic mode, and categories against the
    one opponent in tactical mode.
- **Projected average** (used for ranks and differences):
  - additive: the mean of the team totals;
  - ratio: mean(makes) / mean(attempts), a ratio of means and never a mean of ratios
    (Constitution I).
- **Ranks**: competition ranking (1, 2, 2, 4), with the direction applied. Ranks are always among
  all league teams, in both modes, under that mode's scaling.

## R4. Availability rate (strategic mode)

**Decision**: p = games played ÷ team games, computed over [the oldest game in the player's X-game
window, the analysis date].

- **Team games** are the player's team's final regular-season games in that span, counted by stint.
  This is the 001 `get_availability` logic, done in bulk.
- **The span ends at the analysis date**, not at the player's last game, so a player who has been
  out for a month gets a low p.
- **Games played** in the span are exactly the window's games, because the window is the
  player's last X games.
- **Edge values**: p is capped at 1. A player with no games has no p and contributes nothing
  anyway. A player with no team games in the span gets p = 1, for example a player whose window
  is entirely in last season and whose current team hasn't played yet.

**Analysis date** (`as_of`): every request carries it, and it defaults to the server's current
date. It sets:
- the X-game window cutoff;
- the end of the availability span;
- tactical "games remaining from today";
- the default tactical period (the Monday–Sunday week containing `as_of`).

Making it a parameter is what makes SC-002 and the tactical tests reproducible.

## R5. Tactical mode

**Decision**:
- **Games per player**: k = scheduled regular-season games for the player's team (by stint) from
  `as_of` through the end of the period, with status `scheduled`. Games already final, postponed
  or cancelled don't count. This is the 001 `count_team_games(statuses=("scheduled",))` logic,
  done in bulk.
- **Statuses** (Q, O, DTD) are displayed but not modeled (spec assumption).
- **No opponent chosen**: tactical results aren't computed, and the response says an opponent is
  required.
- **All k = 0** (no games remaining): the response sets a "no games remaining in period" warning,
  and the record shows 0 games.

## R6. Display series

All series are computed on the server. The frontend only draws them (Constitution stack rule:
"the frontend MUST NOT re-implement statistical or scoring logic").

- **Radar**: one series per team. Each series is the team's rank in every category. Radial scale:
  rank 1 at the rim, rank N at the center.
- **Category curves**: a Gaussian kernel density (Scott's bandwidth) over a 96-point grid that
  spans the 0.5th–99.5th percentile of all plotted series for that category. Each category's
  density is computed from a 2,000-sample subsample of the simulations. Display only; the
  statistics use every simulation.
- **"League leader"** in a category is the team ranked 1 by projected average. If the selected
  team is ranked 1, the overlay is the #2 team, labeled "next best", so the comparison is never
  empty.
- **"League average"** is the pooled distribution of every team's simulated totals: what a
  randomly chosen opponent looks like. That is the head-to-head reading. The spread of the
  per-simulation mean is much narrower and would understate how variable an opponent is.
- **Tactical overlays**: the opponent only, in curves and radar. Radar ranks are still among all
  teams under tactical scaling.

## R7. Moves and the scenario

**Decision**:
- **Stateless server**: every analysis request carries the base league ID plus an ordered move
  list. The server rebuilds the scenario from the loaded league snapshot (001 `get_league`) by
  applying the moves as pure transitions (Constitution VII).
- **Session persistence**: the browser keeps the settings and moves in `sessionStorage` (spec
  assumption: the session lasts until reload or reset).
- **Validation**: moves are validated in order. The first invalid move rejects the request with
  HTTP 422 and `{move_index, code, message}`. The codes are `NOT_ON_TEAM`, `NOT_FREE_AGENT`,
  `NO_ACTIVE_SLOT`, `SAME_TEAM`, `RESERVE_SLOT` and `UNKNOWN_PLAYER`.
- **What the server reports** (it computes all of it, so the frontend never applies the rules
  itself):
  - each team's open active slots;
  - for each picker row: `can_add`, `swap_options`, and the reason "+" is disabled when it is.
- **Move semantics**:
  - **drop(p)**: p leaves its team for the free-agent pool. A dropped reserve player frees no
    active slot.
  - **add(p)**: p must be a free agent, and the selected team needs an open active slot. p takes
    an active slot.
  - **swap(acquire = P from T, give = Q)**:
    - If Q is on the selected team, it is a 1-for-1 trade. Q takes P's place on T in an active
      slot, and P joins the selected team in an active slot. No open slot is needed, and Q may
      come from a reserve slot.
    - If Q is a free agent, Q joins T in an active slot, and P joins the selected team, which
      needs an open active slot.

## R8. API shape (FastAPI)

**Decision**: a small JSON API under `/api`; contracts/api.md gives the full shape.

- `GET /api/leagues` lists the leagues.
- `GET /api/leagues/{id}` returns the base snapshot and data freshness.
- `POST /api/impact/analyze` returns the full analysis for settings plus moves.
- `POST /api/impact/players` returns the picker list for settings plus moves, with optional search
  text.

Separating the picker keeps the analysis payload small (about 550 picker rows versus about
60 KB of series), and lets search run without re-simulating. Pydantic models are the contract,
and TypeScript types are generated from `/openapi.json` with `openapi-typescript`.

**Caching**:
- **Projection cache**: player projections (fits, availability) are keyed by
  (league, `as_of`, X, latest `load_run` ID) in a process-level LRU. A move never refits; only new
  data or new settings do.
- **No result caching**: simulation results are not cached; at about 0.2 s, recomputing is cheap.

## R9. Frontend

**Decision**:
- **App**: React 19 + TypeScript, built with Vite, as a single page.
- **Charts**:
  - the radar in D3 (`d3-scale`, `d3-shape`), since Plot has no radial layout;
  - the category curves in Observable Plot (`Plot.areaY` / `Plot.lineY`).
- **Data fetching**: plain `fetch` with an `AbortController`, and a 250 ms debounce on settings
  that change continuously (window X, search). No state-management library: the state is just
  settings plus moves.
- **Styling**: plain CSS with tokens taken from `docs/style.md`:
  - Helvetica Neue only;
  - black, white and yellow chrome;
  - no border-radius, shadows or gradients;
  - a red outline for "−".
- **Data-mark colors** (from the style guide's palettes; darker means more important):
  - selected team: primary `#1C324A`, full opacity;
  - other teams (strategic radar): primary `#9DC0F5` at 35% opacity;
  - opponent (tactical): secondary `#A96043`;
  - league leader or next best: secondary `#CE7955`;
  - league average: tertiary `#898240`.
- **Testing**: Vitest + React Testing Library, with a mocked API, for:
  - eligibility-driven controls (+, −, swap dialog);
  - asterisk footnotes;
  - mode-specific panels.

  Browser end-to-end checks are a manual quickstart step.
- **Prerequisite**: Node 22 LTS. **It is not installed on this machine** (no `node` or `npm`).
  Installing it with `brew install node@22` needs the user's approval.

**Alternatives considered**:
- **Recharts or ECharts**: excluded by the constitution (Plot and D3 only).
- **TanStack Query**: helpful, but unnecessary for two endpoints and one in-flight request.

## R10. Layering and packaging

**Decision**: new Python packages, following Constitution VII.

```text
ffmodel/core/scoring/    # format interface + nine_cat_h2h + registry
ffmodel/core/model/      # projections: fit, availability, games remaining
ffmodel/core/sim/        # Monte Carlo engine (projection-in, samples-out; DB-free)
ffmodel/core/scenario/   # immutable league scenario + move transitions
ffmodel/core/data/       # (001) + bulk reads: last-N for many players, team games, freshness
ffmodel/tools/impact_analysis/   # orchestration → AnalysisResult
ffmodel/api/             # FastAPI app; thin routes → tools
```

- **New import-linter contracts**:
  - `core` must not import `tools` or `api`;
  - `tools` must not import `api`;
  - `adapters` must not import `tools` or `api`.
- **Testable without a database**: the simulation engine takes `PlayerProjection` objects
  directly, so SC-004, SC-005 and SC-006 run as fast tests on synthetic projections.
- **New dependencies**:
  - runtime: `numpy`, `fastapi`, `uvicorn[standard]`;
  - dev: `httpx`, for the FastAPI test client.

  `numpy` is already present transitively through `nba_api`; it becomes a direct dependency.
- **New CLI command**: `ffm serve`. It runs uvicorn and serves `frontend/dist` when it exists.
