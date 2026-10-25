# Data Model: Recency-Weighted Player Projections

No schema change. These are in-memory model entities in the core and the settings that feed
them.

## PlayerProjection (core.model.fit), changed

| Field | Type | Change | Meaning |
|---|---|---|---|
| player_id | int | — | |
| games_found | int | — | games played in the lookback (used by the footnote) |
| games_requested | int | — | the *Last X games* setting |
| mean | per-stat vector | **weighted** | weighted per-game means, after shrinkage when a prior is applied |
| chol | matrix or None | **weighted** | Cholesky factor of the shrunk weighted covariance |
| mean_stderr | per-stat vector | **uses n_eff** | √(diag Σ / *n*eff), the fit error |
| availability | float or None | — | unchanged: most recent 15 games (research R5) |
| games_remaining | int | — | unchanged (tactical) |
| effective_games | float or None | **new** | (Σ*w*)²/Σ*w*²; None means "equals games_found" |

**Derived**: `n_eff` = `effective_games`, or `games_found` when it's None. `is_short` =
games_found < games_requested (unchanged).

**Validation**:
- with no games, there's no fit (`chol` is None), as today;
- `effective_games` ≤ `games_found`, with equality exactly when all weights are equal.

## Game weight (computed, not stored)

*w*ⱼ = 0.5^(*j* / 40) × 0.25^*a*ⱼ:
- *j*: games ago (0 = most recent);
- *a*ⱼ: start year of the as-of date's season − start year of game *j*'s season.

Constants `RECENCY_HALF_LIFE = 40`, `SEASON_WEIGHT = 0.25` (core.model.fit).

## MeanPrior (core.model.fit), changed

| Field | Type | Change |
|---|---|---|
| mean | per-stat vector | — the typical player's means (*m*) |
| true_var | per-stat vector | — between-player spread net of sampling error (*τ*²) |
| ratios | tuple of RatioPrior | — one per percentage |
| caps | tuple of (small, big) | — subset constraints |
| real_share | per-stat vector | — diagnostic |
| exempt | tuple of stat indices | **new**: stats left unshrunk (from the format) |

Built by `estimate_prior(fits, ratio_pairs, caps, exempt)`. The pool is fits with games_found ≥
5. It returns None when the pool has fewer than 30 players. Per-player makes and attempts use
`n_eff`.

## RatioPrior (core.model.fit), unchanged

made index, attempts index, league rate, *κ* (prior strength in attempts), real_share.

## ScoringFormat (core.scoring.base), changed

| Field | Type | Change |
|---|---|---|
| unshrunk_stats | tuple of base-stat names | **new**, default `()`; 9cat: `("blk",)` |

**Validation (conformance)**: every name is in `base_stats`.

## AnalysisSettings / ScenarioRequest, changed defaults

| Field | Before | After |
|---|---|---|
| window | default 15 (range 1–82) | default **82** (range 1–82), meaning "most games a fit looks back" |

## Relationships

`build_projections(window, as_of)`:
1. fetches each player's last *window* games;
2. fits with weights, giving a PlayerProjection with `effective_games`;
3. applies `shrink_projection` with the settings' MeanPrior, built once per settings key from the
   past-year pool, with `exempt` from `ScoringFormat.unshrunk_stats`;
4. sets availability from the most recent 15 of those games.
