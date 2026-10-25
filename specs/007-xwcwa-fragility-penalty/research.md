# Research: xLift in Impact Analysis and the Fragility Penalty

## R1. Where xLift lives: a DB-free core module

**Decision**: `core/value/xlift.py` holds xLift's maths, taking arrays only:
- the team per-period totals matrix *T* (teams × base stats);
- the per-category weekly difference spread *s_c*;
- the scoring format.

It exposes:
- `team_keys(T, fmt)`: per-category keys via `fmt.category_values` + `rank_key`, with derived
  stats.
- `expected_wins(keys_t, keys_others, spread)`: Σ_c Σ_u Φ((k_tc − k_uc)/s_c), the expected
  category wins of team *t* in a week.
- `weakest(team_idx, active_lines, T, …)`: the active line whose removal (slot empty) loses the
  fewest expected wins. A line of zeros (no projection) is weakest by definition.
- `score_candidates(team_idx, candidate_lines, out_line, …)`: the expected wins after swapping
  each candidate in for `out_line`, minus current.
- `score_own(team_idx, own_lines, weakest_line, …)`: the expected wins now, minus the expected
  wins with each own player replaced by `weakest_line`.

**Rationale**: Constitution VII (computing core is DB-free and testable). Principle II (only
`fmt` knowledge). Vectorized over candidates with NumPy (about 500 × 9 × 17).

**Equivalence with the notebook**: the notebook's weekly curve is *R*(*x*) = 1 + Σ_u
Φ((k_u − x)/(√2σ_c)), and its gain is *R*(old) − *R*(new). That's exactly the change in Σ_u
Φ((x − k_u)/(√2σ_c)), the expected wins. So *s_c* = √2 × the median per-team weekly SD, the
same as the notebook (SC-001).

**Alternatives considered**: putting it in the tool (it isn't reusable by other tools; violates
VII's "shared domain logic in core"); in TypeScript (forbidden: the frontend renders only).

## R2. Weekly spreads: a seeded per-period simulation of every team

**Decision**: per settings key and fragility option, simulate each team's per-period totals with
the strategic games sampler. Use 4,000 iterations, seed 20261024 and mode code 1, as the
notebook does. Take the per-category SD per team, and the median over teams. The difference
spread is √2 × that.

The spreads are computed for the **base (no-move) scenario** and reused under moves.

**Rationale**:
- FR-006 asks for spreads from the analysis's own simulation.
- Strategic mode's existing 25,000-iteration samples could serve, but tactical mode has none.
  One separate, smaller, cached run serves both modes and matches the notebook.
- Spreads are a league-level scale; a single move barely changes a median over 18 teams.
  Reusing them keeps a move's xLift comparable to the original's.

**Alternatives considered**:
- **Analytic variance**: easy for counting stats, but needs the delta method for ratios.
- **Reusing strategic samples**: doesn't exist in tactical mode.

## R3. dAB in the app

**Decision**:
- `core/model/availability.py` (DB-free) ports `analysis/availability.py`'s per-player counts
  and blend:
  - counts by season age (window played and team games, long-run played and team games over
    the last 3 seasons; 6 age buckets);
  - weighted with δ^age;
  - window and long-run rates shrunk toward ā with κ_w and κ;
  - blend ā + b₁(window − ā) + b₂(long − ā), clipped to [0, 1].
- **Constants**, recorded from the availability backtest (2022-23 to 2025-26): ā = 0.770113,
  δ = 0.05, κ = 5, κ_w = 0, b₁ = 0.586418, b₂ = 0.144796, window 15 games, lookback 3 seasons.
- **Tag multipliers**: IL/IL+ 0.3, O 0.6, Q/GTD/DTD 0.9, SUSP 0.7, NA 0.0.
- `core/data/history.py` reads each requested player's regular-season played dates and
  team-game dates (via stints), the season list, and each season's game days. It infers missed
  seasons exactly as the analysis module does: a season with no appearances between two with
  appearances becomes a team's worth of evenly spaced missed dates, known from the return.

**Rationale**: FR-015 to FR-017, SC-005 (match the analysis module within 0.001). Fixed
constants per the user's decision. The reads only cover the players a request needs.

**Alternatives considered**:
- **Importing `analysis/availability.py` from the backend**: wrong direction (analysis isn't
  part of the app), and it would add a polars dependency.
- **Refitting at request time**: seconds of work, and the user wants fixed parameters.

## R4. Applying the Fragility Penalty

**Decision**: `tools/impact_analysis/fragility.py` maps (option, projections, scenario, statuses,
dAB) to projections with availability replaced (`dataclasses.replace`), applied to all
projections before `_compute` and before xLift:

| Option | Availability |
|---|---|
| `none` | 1.0 for players outside the selected scenario's reserve slots; 0.0 in a reserve slot |
| `last15` | as built (the 15-game estimate) |
| `dab` | dAB |
| `dab_tag` | dAB × tag multiplier |

Players without a projection stay unprojected under every option.

**Rationale**:
- The simulation reads availability only from `proj.availability` (strategic games sampler),
  so one substitution covers every strategic result (FR-013).
- **Tactical**: the matchup simulation uses games remaining, not availability, so it's
  unaffected (FR-018). xLift uses the substituted availability.
- **`none` and reserve slots**: "IL slot" = the roster's reserve slot (IL/IL+/NA). Slots belong to
  the scenario (every team's, not only the selected team's), so a player moved to a reserve slot counts. Free agents have no slot: 1.0.

## R5. Per-period lines for xLift

**Decision**: line = projection mean × availability (after the Fragility Penalty) × games per
period. In tactical mode, games per period is the settings' value (default 3). Team totals sum
active players' lines.

**Rationale**: FR-004; it matches the notebook's `lines` and team totals.

## R6. xLift on roster rows

**Decision**: `_roster_rows` gains `xlift` per player. Each team's rows are scored for that
team:
- active players get `score_own` against the team's weakest active line;
- reserve players get `score_candidates` (as if they replaced the weakest), with the existing
  `slot` field marking them as not counted (FR-009);
- players without a projection get `None`.

**Rationale**: covers FR-009 and FR-011 (the opponent's rows are scored for the opponent) in
one place, for every team in the response.

**Implementation note**: the weakest player is chosen by removal cost, but own players are
scored by a swap for a copy of it. FG% and FT% aren't additive, so the two orders can disagree,
and a high-volume, low-percentage player can score slightly below 0 (2 of 176 active players on
the real league under dAB × tag; none under Last 15). The value is still that swap's effect.

## R7. Picker: score the pool, sort, then page

**Decision**:
1. `list_players` builds the candidate list as today (eligibility, search, free-agent filter).
2. It gets projections for **all** candidates through the projection cache, applies the
   fragility option, and scores them with `score_candidates` for the selected team in the
   current scenario (moves included).
3. It sorts free agents first, then rostered players. Within each group: xLift descending, then
   name; unprojected players last.
4. Then it pages.

**Rationale**: FR-010 and SC-003 (order holds across pages and filters). The pool is about 500
players; scoring is vectorized and cheap once projections are cached. The cost is the first
fetch of those players' windows; the 006 pool fetch already covers most of them (see R8).

## R8. Caching and performance

**Decision**:
- **dAB**: cached per (database URL, as-of, load run) for the players fetched, extended on
  demand like the projection cache.
- **Spreads**: cached per projection-cache key + fragility option.
- **Projections**: the picker reuses the projection cache. Its windows come from the 006 prior
  pool (players with a game in the past year), so most picker players are already fetched in
  the same bucket.

Estimated cold costs, to be measured in quickstart:
- dAB reads: one query each for played dates, team dates and season days, restricted to the
  needed ids, about 0.1–0.3 s for about 500 players;
- spread simulation: about 0.05 s (18 × 4,000);
- xLift: under 0.01 s.

**Rationale**: SC-006 (cold analysis ≤ 1.38 s, picker < 1 s).

## R9. API and UI

**Decision**:
- **Request:** `ScenarioRequest.fragility: Literal["none", "last15", "dab", "dab_tag"] =
  "dab_tag"`, echoed in `SettingsEcho`.
- **Rows:** `RosterPlayer.xlift: float | None` and `PlayerRow.xlift: float | None`.
- **Frontend:**
  - state default `dab_tag`;
  - a dropdown labeled "Fragility Penalty" with options None, Last 15, dAB, dAB × tag;
  - an "xLift" column (signed, 2 decimals) in the roster and picker tables;
  - help entries for the column and the dropdown, with no file names (project rule);
  - the picker renders the server's order.
- **Saved state:** the storage key moves to v3, since a new setting changes the saved-state
  shape.
- **Generated types:** regenerated with `npm run gen:api`.

**Rationale**: Constitution (Pydantic is the contract, generated TS types, frontend renders only).

## R10. Parity checks and tests

**Decision**:
- `analysis/xlift_parity.py` runs the app's code path (`analyze` and `list_players`) and the
  rankings notebook's computation (`app.run()` with the matching settings: weekly curve,
  weakest-player swap, window 82, games per period 3) for one team. It reports the maximum
  |Δ xLift| over free agents (SC-001, ≤ 0.05).

  The comparison runs under **Last 15** (the notebook's "Window" availability). The notebook
  always takes its weekly spreads from the window availability, while the app uses the selected
  option throughout. Only under Last 15 do both use identical lines and spreads, so differences
  reflect the xLift code, not a modeling choice. Both sides take spreads from the shrunk
  projections (T031 aligns the notebook's weekly-noise cell). dAB parity is checked separately (SC-005). It also compares dAB for all rostered
  players against `analysis/availability.py` (SC-005, ≤ 0.001).
- **Unit tests** (DB-free) on synthetic leagues:
  - win odds and the tie rule (equal keys give 0.5);
  - TO direction;
  - ratio recompute after a swap;
  - the weakest-player rule (zero line weakest);
  - own-player baseline (the weakest gets 0);
  - empty-slot candidates;
  - determinism.
- **dAB unit tests:** counts by age, missed-season inference, the blend, clipping, and tag
  multipliers.
- **Integration tests:**
  - Last 15 results equal the pre-feature results (SC-004);
  - None gives availability 1 outside reserve slots and 0 in them;
  - dAB × tag scales tagged players only;
  - picker order and paging consistency;
  - opponent rows scored for the opponent in tactical mode;
  - SC-007 (adding the top free agent in place of the weakest player changes expected wins by
    its listed xLift, within ±0.05).
