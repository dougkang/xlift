# Data Model: xLift in Impact Analysis and the Fragility Penalty

No schema change. These are in-memory entities in the core and tool, plus contract fields.

## AnalysisSettings (tool), changed

| Field | Type | Default | Notes |
|---|---|---|---|
| fragility | `"none" \| "last15" \| "dab" \| "dab_tag"` | `"dab_tag"` | applies to the whole analysis (FR-013) |

It's part of the settings echo and of the cache keys for spreads and the original analysis.

## FragilityOption → availability (per player)

| Option | Availability |
|---|---|
| none | 1.0 if not in a reserve slot of the scenario, else 0.0 |
| last15 | the projection's 15-game estimate (unchanged) |
| dab | dAB(player, as-of) |
| dab_tag | dAB × TAG_MULTIPLIER[status] (1.0 if the status has no multiplier) |

**Validation**: availability ∈ [0, 1]. A player with no projection (no games) gets none under
every option.

## DabParams (core.model.availability), constants

| Name | Value | Meaning |
|---|---|---|
| ABAR | 0.770113 | pool availability rate |
| DELTA | 0.05 | weight per season of age |
| KAPPA | 5 | long-run prior strength (team games) |
| KAPPA_W | 0 | window prior strength |
| B1, B2 | 0.586418, 0.144796 | blend weights (window, long run) |
| WINDOW | 15 | window games played |
| LOOKBACK_SEASONS | 3 | long-run reach |
| AGES | 6 | season-age buckets (older pool into 5) |
| TAG_MULTIPLIERS | IL/IL+ 0.3, O 0.6, Q/GTD/DTD 0.9, SUSP 0.7, NA 0.0 | dAB × tag |

## AvailabilityHistory (core.data.history), read result

| Field | Type | Meaning |
|---|---|---|
| seasons | list of (season_id, first day, last day, games) | seasons with final games ≤ as-of |
| played | {player → ascending game dates} | regular-season games played |
| team_games | {player → ascending dates} | games of the player's team(s) while on the roster |
| missed | {player → [(dates, known_from)]} | inferred missed seasons |

## AgeCounts (core.model.availability)

A 4 × AGES matrix per player at a cutoff:
- rows: window played, window team games, long-run played, long-run team games;
- columns: season age.

dAB = clip(ā + B1·(w̃ − ā) + B2·(l̃ − ā), 0, 1). Here w̃ and l̃ are the weighted (δ^age)
window and long-run rates, shrunk with κ_w and κ, with ā used when there's no evidence.

## Per-period line and team totals (tool.value)

- line_i = projection mean × availability × games per period (a base-stat vector)
- T_t = Σ over active players of line_i; reserve players excluded

## WeeklySpread (tool.value, cached)

A per-category s_c = √2 × median over teams of the SD of a team's simulated per-period category
value. It uses 4,000 iterations, seed 20261024, and the base (no-move) scenario.

## xLift value

Per (team t, player i), in expected weekly category wins:
- **candidate** (not active on t): W(T_t − line_weakest + line_i) − W(T_t)
- **own active player**: W(T_t) − W(T_t − line_i + line_weakest)

Here W(·) = Σ_c Σ_{u≠t} Φ((k_c(·) − k_uc)/s_c), with keys direction-adjusted (`rank_key`).
Weakest = the active line minimizing W(T_t) − W(T_t − line); a zero line wins ties.

## Contract fields

- `RosterPlayer.xlift: float | None`, scored for the row's own team.
- `PlayerRow.xlift: float | None`, scored for the request's selected team.
- `SettingsEcho.fragility`.
