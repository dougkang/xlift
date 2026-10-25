# Research: Recency-Weighted Player Projections

All decisions are backed by backtests over the loaded seasons (2022-23 to 2025-26), scored on
the three seasons that have a prior season, leaving one season out. Unless noted, "error" is the
mean squared error of per-game projections against what the player did next, compared with the
current 15-game equal-weight window.

## R1. Weighting: games-based exponential decay with a per-season discount

**Decision**: game *j* games ago (0 = most recent) weighs 0.5^(*j*/40) × 0.25^*a*, with *a* the
season age. Look back over up to *X* games played, where *X* is the user setting (default 82).
The half-life and season weight are fixed constants.

**Rationale**:
- With 6,847 player-cutoffs (early and mid-season), the best settings are a broad plateau.
  Any lookback of 82+ games with a half-life of 20–60 games scores within about one point of the
  best. Held-out-season picks give 22%, 23% and 17% lower counting-stat error than the window.
- The settings hold across horizons (2,493 early-season player-cutoffs):

  | Horizon | Best (lookback, half-life, season weight) | Error reduction | (82, 40, 0.25) |
  |---|---|---|---|
  | next 15 games | 120, 40, 0.25 | 25.0% | 24.8% |
  | next 30 games | 120, 60, 0.25 | 28.9% | 28.5% |
  | next 60 games | 120, 60, 0.25 | 29.9% | 29.1% |

  Half-life 40 is within 0.5 points of the best at every horizon, so one setting serves weekly
  and season-long use. The season weight stays 0.25. At 60 games, 0.5 is about equal; there's
  no sign that one-season breakouts need extra discounting.
- Weighting by **games** rather than by date means time missed doesn't erode a player's history.
  Absence is availability's concern.

**Alternatives considered**:
- **Longer equal-weight window (40–82 games)**: 15–17% better, but 3–5 points behind decay.
- **Lookback 120**: marginally better (≤ 0.8 points), but it caps at 82 to match the existing
  API bound and keep queries small.
- **User-settable half-life**: rejected (the spec keeps the setting count unchanged). The
  plateau makes the choice uncritical.

## R2. Effective number of games replaces the game count

**Decision**: *n*eff = (Σ*w*)²/Σ*w*² replaces *n* in:
- the covariance shrinkage λ = 5/(*n*eff − 1 + 5);
- the fit error *se* = √(diag Σ / *n*eff);
- the mean shrinkage's per-player makes and attempts (rate × *n*eff).

The weighted covariance uses reliability weights: Σ*w*(*x*−μ)(*x*−μ)ᵀ / (Σ*w* − Σ*w*²/Σ*w*).

**Rationale**: with equal weights, every formula reduces exactly to today's (*n*eff = *n*,
denominator *n* − 1), so the change is a strict generalization and existing tests keep pinning
the unweighted path. Decayed fits correctly read as less certain. Example *n*eff at the current
as-of date: about 36–40 for regular veterans, 8.4 for a player back from a missed season, and 2
for a two-game rookie.

**Alternatives considered**: keeping *n* (overstates certainty for decayed or old histories);
using Σ*w* (not scale-free).

## R3. Mean shrinkage (documenting the post-005 addition)

**Decision**: empirical Bayes per stat, with the prior estimated from every player with a game in
the past year and 5+ games in the lookback, fit the same way:
- **Counting stats**: *m* + *w*(*x̄* − *m*), with *w* = *τ*²/(*τ*² + *se*²) and *τ*² = Var(*x̄*) −
  mean(*se*²).
- **Percentages**: beta-binomial, (makes + *κ*·rate)/(attempts + *κ*), with *κ* = rate(1 − rate)/
  *τ*ₚ² − 1, then makes = shrunk rate × shrunk attempts. Subset caps (3PM ≤ FGM) reapplied.
- **No shrinkage when fewer than 30 players qualify** (e.g. the test fixture).

**Rationale**, measured on top of the weighted fit:
- **Counting stats**: +1–3% over 15 games, up to +4–9% over 60 (steals, threes, turnovers).
  Stars' (20+ pts) points bias drops from about +1.0 to +0.1–0.2 a game.
- **Percentages** (20,569 player-cutoffs, attempt-weighted): FG% −11% and FT% −17% error over 15
  games; −20% and −32% for low-volume shooters; FT% −29% over 60. Calibrated across the range
  (90%+ FT shooters projected .856, shot .859).
- **Ranking impact**: on today's rankings, shrinkage moves established players a median of 4
  spots and players with fewer than 10 effective games a median of 50. Without it, a 1-game
  player ranked 97th.

**Alternatives considered**:
- **Minimum-games cutoff**: discards information and needs its own threshold.
- **Shrinking only small samples**: the backtest favors shrinking everyone (stars' bias).
- **Role- or position-aware prior**: deferred. It would fix the blocks and FG%-extremes issues
  (R4).

## R4. Blocks exemption lives in the scoring format

**Decision**: add `unshrunk_stats: tuple[str, ...] = ()` to `ScoringFormat`. The 9cat module sets
`("blk",)`. `build_prior` maps the names to indices and passes them to `estimate_prior`, which
records them in `MeanPrior.exempt`. `shrink_projection` leaves those means unchanged.

**Rationale**:
- **Principle II** forbids stat names hard-coded outside a format module, so the draft's
  `UNSHRUNK_STATS = ("blk",)` in `projection.py` must move.
- **Evidence**: shrinking blocks raised error for players overall at every horizon (−1.8% to −3.5%)
  and was noisy for stars (+10% to −28%). A center's block rate is skill.

**Alternatives considered**: a core-level constant (violates II); a settings field (not a user
choice).

## R5. Availability stays a 15-game measure

**Decision**: compute availability from the most recent `AVAILABILITY_GAMES = 15` games of the
fetched window. Use the same short-history rule as today: when the player has fewer than 15
games in total, count back to their first stint.

**Rationale**: FR-013 and SC-004 require identical availability. Without decoupling, a window of
82 would silently turn availability into a season-long rate. dAB is out of scope.

## R6. Window setting and footnote

**Decision**: the default *X* becomes 82 in settings, the API request model and the frontend
state. The range stays 1–82. The footnote rule is unchanged (games found < *X*). The help text
changes per FR-015.

**Rationale**: the API already bounds the window at 82. Keeping the footnote on games played
follows the spec's assumption. Showing effective games is a follow-up.

## R7. Prior caching and performance

**Decision**: keep the earlier draft's per-settings prior cache in `tools/impact_analysis/
cache.py`, keyed like the projection cache (URL, league, as-of, window, mode, period, format,
load run). The prior is built once per key and shared by every projection in the bucket.

**Rationale**: the prior's pool doesn't depend on which players a request asks for (FR-012).
At 82 games the bulk query returns about 5× the rows. Implementation measurements on the same
four-season database: cold analysis 0.67 s before the feature, 1.22 s with the first draft
(1.82×, over SC-006). Two behavior-preserving fixes brought it to 0.92 s (1.37×):
- the bulk read builds game lines from positional rows instead of a dict per row;
- the cache fetches the prior's pool windows once (`prior_pool_windows`) and passes them to
  both `build_prior` and `build_projections`, which fetches only players outside the pool.

A test pins that reused windows give identical projections.

## R8. Testing approach

**Decision**:
- **Unit (DB-free)**:
  - the weighted fit with equal weights equals the current fit;
  - hand-computed weighted mean, covariance and *n*eff for small windows;
  - season age, including a missed season;
  - λ and *se* use *n*eff;
  - shrinkage formulas and ratio counts on *n*eff;
  - the exemption leaves blocks unshrunk;
  - no prior under 30 players.
- **Scoring conformance**: `unshrunk_stats` ⊆ `base_stats`.
- **Integration (fixture)**: availability at window 82 equals availability at window 15; the
  prior is wired through `build_projections`; footnote tests updated for the new default.
- **Determinism**: an existing seed test re-run at the new default.

## R9. Reproducible backtest for the success criteria

**Decision**: add `analysis/projection_backtest.py`. It's a script, not a notebook, built on
`analysis/minutes.py` loading. It scores the 15-game window, the weighted fit and the weighted
fit plus shrinkage, using the **backend's** `fit_projection` / `estimate_prior` /
`shrink_projection`, so it measures the shipped code. It reports SC-001 (counting stats, next 15
games), SC-002 (next 30 and 60), SC-003 (stars' points bias) and SC-007 (FG% and FT%,
attempt-weighted), with pass or fail against the thresholds.

**Rationale**: the backtests behind this spec ran as throwaway scripts. The criteria need a
durable, rerunnable instrument.
