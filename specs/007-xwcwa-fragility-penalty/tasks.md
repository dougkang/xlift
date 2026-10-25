---

description: "Task list for 007 xLift in Impact Analysis and the Fragility Penalty"
---

# Tasks: xLift in Impact Analysis and the Fragility Penalty

**Input**: Design documents from `/specs/007-xwcwa-fragility-penalty/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: included. The constitution's quality gates require core tests, and research R10
lists them.

**Organization**: tasks are grouped by user story (spec.md). US1 and US2 (P1) share the xLift
core (Foundational), and US3 (P2) adds the Fragility Penalty. Don't touch `docs/overview.md` or
`docs/tool2-player-comparison.md`; they're the user's own uncommitted edits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 per spec.md

---

## Phase 1: Setup

- [X] T001 Create a branch for the feature from the current tip of `006-recency-weighted-projections`: `git switch -c 007-xwcwa-fragility-penalty`. Then record the baseline: `uv run pytest -q` in `backend/` and `npm test` in `frontend/` must pass before any change.
- [X] T002 Record pre-feature fixture results for SC-004. With the pre-feature code, run `analyze` on the impact fixture (`backend/tests/fixtures/impact_dataset.py`, teams ALPHAS and DELTAS, strategic, default settings) and save `header`, `matchups`, `category_table`, `radar` and `curves` as JSON to `backend/tests/fixtures/pre007_strategic.json`, using a short script in the job temp folder.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the DB-free xLift core and the tool's line and spread plumbing, which US1, US2 and
US4 all use

- [X] T003 [P] In `backend/tests/unit/test_xlift.py`, write DB-free tests for the module in T004. Build a 4-team synthetic league with 9cat (`get_format("9cat_h2h")`) and cover:
  - equal keys give a 0.5 win probability per opponent (tie rule);
  - for TO, a lower team value raises expected wins;
  - FG% after a swap equals (team FGM − out FGM + in FGM) / (team FGA − out FGA + in FGA);
  - the weakest active player is the one whose removal loses the fewest expected wins, and a zero line (no projection) is always weakest;
  - `score_own` gives exactly 0 for the weakest player;
  - a candidate filling an empty slot uses a zero out-line;
  - results are deterministic.
- [X] T004 Create `backend/src/ffmodel/core/value/__init__.py` and `backend/src/ffmodel/core/value/xlift.py` (DB-free, NumPy, research R1). Implement:
  - `team_keys(T, fmt)`, for T of shape (..., base stats): add `fmt.derived_stats`, then `fmt.rank_key(fmt.category_values(...))`;
  - `expected_wins(team_idx, K, spread)` = Σ_c Σ_{u≠t} Φ((K[t,c] − K[u,c]) / spread[c]), using a vectorized normal CDF (e.g. the Abramowitz–Stegun erf used in `analysis/player_rankings_analysis.py`);
  - `weakest(team_idx, T, active_lines, fmt, spread)`, returning the index of the line minimizing W(T_t) − W(T_t − line);
  - `score_candidates(team_idx, T, out_line, candidate_lines, fmt, spread)`, giving W(T_t − out + cand) − W(T_t) for every candidate (vectorized);
  - `score_own(team_idx, T, own_lines, weakest_line, fmt, spread)`, giving W(T_t) − W(T_t − own + weakest).

  Docstrings cite spec FR-001–FR-006. Make T003 pass.
- [X] T005 Create `backend/src/ffmodel/tools/impact_analysis/value.py` (research R2, R5). Implement:
  - `lines(projections, games_per_period)` → {player: mean × availability × games_per_period}, skipping projections with `games_found == 0`;
  - `team_totals(scenario, lines, base_stats)` → (team_ids, T), summing active players;
  - `weekly_spread(scenario, projections, fmt, games_per_period)`: for each team, `simulate_team(..., strategic_k(games_per_period), iterations=4000, seed=20261024, mode_code=1)`; per-category nanstd; median over teams; × √2;
  - `score_rows(scenario, projections, fmt, games_per_period, spread)` → {team_id: {player_id: xlift or None}}, scoring active players with `score_own` and reserve players with `score_candidates`;
  - `score_pool(scenario, team_id, pool_projections, fmt, games_per_period, spread)` → {player_id: xlift or None}, scoring with `score_candidates` against the team's weakest active line.
- [X] T006 In `backend/src/ffmodel/tools/impact_analysis/cache.py`, add a `spread(conn, settings, compute)` cache keyed by the projection-cache key + `settings.fragility` + `settings.games_per_period`. It's computed from the **no-move** scenario (research R2) and cleared by `clear()`.
- [X] T007 Add `fragility: str = "dab_tag"` to `AnalysisSettings` in `backend/src/ffmodel/tools/impact_analysis/settings.py`, with allowed values `"none" | "last15" | "dab" | "dab_tag"` (data-model.md). Add `settings.fragility` to the `original(...)` cache key in `backend/src/ffmodel/tools/impact_analysis/cache.py`.

**Checkpoint**: `uv run pytest -q tests/unit/test_xlift.py` passes, and the full suite is still
green.

---

## Phase 3: User Story 1 - Find the free agents worth adding (P1) 🎯 MVP

**Goal**: the picker shows xLift for the selected team and sorts by it (FR-010, SC-003, SC-007).

**Independent Test**: the impact fixture's picker with `free_agents_only=True` returns
non-increasing `xlift`, consistent across `offset` pages and with a `query`.

### Tests for User Story 1

- [X] T008 [P] [US1] In `backend/tests/integration/test_xlift_rows.py`, add picker tests on `impact_engine`:
  - every free agent with a projection has a float `xlift`;
  - free agents' `xlift` is non-increasing, ties ordered by name, unprojected (`None`) last;
  - pages (`offset` 0 and 3, `limit` 3) concatenate to the full order;
  - a `query` keeps the relative order;
  - rostered players follow free agents, also by `xlift`;
  - SC-007: applying `Add(top FA)` + `Drop(weakest active)` changes the team's expected weekly wins (via `value.py` on the moved scenario) by the listed `xlift`, within ±0.05.

### Implementation for User Story 1

- [X] T009 [US1] In `backend/src/ffmodel/tools/impact_analysis/picker.py` (research R7):
  1. build the candidate list as today;
  2. get projections for **all** candidates via `cache.projections`, and apply the fragility option (T017; until then, Last 15 as built);
  3. get the spread via `cache.spread`;
  4. score with `value.score_pool` for `s.team_id` in the current scenario (moves included);
  5. sort (free agents first; then `xlift` descending; then name; `None` last);
  6. then page with `offset`/`limit`.

  Add `"xlift"` to each row.
- [X] T010 [US1] In `backend/src/ffmodel/api/schemas.py`, add `xlift: float | None` to `PlayerRow`.
- [X] T011 [P] [US1] In `frontend/src/components/PlayerPicker.tsx`, add an **xLift** numeric column (signed, two decimals, "–" for null; contracts/ui.md), keeping the server's order. Add the **xLift** help entry to `frontend/src/help/content.ts` with contracts/ui.md's wording (no file names). Regenerate `frontend/src/api/schema.d.ts` with `npm run gen:api` (needs `ffm serve`), or hand-add the field if the server can't run.
- [X] T012 [P] [US1] In `frontend/tests/moves.test.tsx` (or a new `frontend/tests/picker-xlift.test.tsx`), test that the picker renders the xLift column and preserves the order of a mocked response. Add `xlift` to the picker fixtures in `frontend/tests/fixtures/`.
- [X] T013 [US1] Run `uv run pytest -q tests/integration/test_xlift_rows.py tests/integration/test_api_moves_players.py` and `npm test`. Update any existing picker test that assumed alphabetical order to the new rule (free agents first, then `xlift`).

**Checkpoint**: the picker ranks free agents for the selected team.

---

## Phase 4: User Story 2 - Each roster player's value to the team (P1)

**Goal**: roster rows show xLift for their own team; the weakest active player shows 0
(FR-002, FR-009).

**Independent Test**: in a fixture analysis, each team's weakest active player has `xlift ==
0.0`, other active players are scored against a copy of it, and reserve rows have a value with `slot == "reserve"`.

### Tests for User Story 2

- [X] T014 [P] [US2] In `backend/tests/integration/test_xlift_rows.py`, add tests:
  - for every team in `analyze(...)["rosters"]` with no open active slot (or the weakest has no projection), exactly one active player has `xlift == 0` (the weakest), and the others equal W(T) − W(T − player + weakest). (Implementation note: these can be slightly negative, because FG% and FT% aren't additive; 2 of 176 active players on the real league under dAB × tag.)
  - for a team with an open active slot, every projected active player has `xlift > 0` and equals W(T) − W(T − player);
  - after a hypothetical move, the values reflect the moved roster;
  - reserve rows carry `xlift` scored as candidates.

### Implementation for User Story 2

- [X] T015 [US2] In `backend/src/ffmodel/tools/impact_analysis/analysis.py`, compute `value.score_rows(...)` for the scenario (with the spread from `cache.spread`). Pass the result into `_roster_rows` and add `"xlift"` to each player dict. For the no-projection path (unsupported format), `xlift` is `None`.
- [X] T016 [US2] Add `xlift: float | None` to `RosterPlayer` in `backend/src/ffmodel/api/schemas.py`. In `frontend/src/components/Roster.tsx`, add the **xLift** column (after *Pos*, or after *G* in tactical mode), signed with two decimals, "–" for null. Reserve rows keep their muted style. Update `frontend/tests/fixtures/strategic*.json` and `tactical*.json` with `xlift`, and add an assertion in `frontend/tests/strategic.test.tsx` that the column renders.

**Checkpoint**: rosters show each player's value.

---

## Phase 5: User Story 3 - Choose how fragility is penalized (P2)

**Goal**: the Fragility Penalty (None / Last 15 / dAB / dAB × tag) drives availability for the
whole analysis (FR-013 to FR-019, SC-004, SC-005).

**Independent Test**:
- Last 15 reproduces `pre007_strategic.json`;
- None gives availability 1 outside reserve slots and 0 inside;
- dAB × tag differs from dAB only for tagged players.

### Tests for User Story 3

- [X] T017 [P] [US3] In `backend/tests/unit/test_availability_dab.py`, write DB-free tests for T019:
  - age-bucket counts for a synthetic history spanning 3 seasons;
  - a missed season adds a team's worth of missed games known only after the return;
  - the blend equals clip(ā + B1(w̃ − ā) + B2(l̃ − ā), 0, 1) with the shrinkage formulas;
  - no evidence gives ā;
  - tag multipliers: IL 0.3, O 0.6, Q 0.9, healthy 1.0.
- [X] T018 [P] [US3] In `backend/tests/integration/test_fragility.py` on the impact fixture:
  - `fragility="last15"` reproduces `tests/fixtures/pre007_strategic.json` exactly (SC-004);
  - `"none"` sets every non-reserve player's availability to 1.0 and reserve players' to 0.0 (check via the projections passed to `_compute`, or via a `fragility.apply` unit call);
  - `"dab_tag"` equals `"dab"` × the tag multiplier for tagged players and equals `"dab"` otherwise;
  - the default is `"dab_tag"`;
  - an invalid value is rejected by the API with 422.

### Implementation for User Story 3

- [X] T019 [US3] Create `backend/src/ffmodel/core/model/availability.py` (DB-free, research R3). It holds:
  - constants `ABAR = 0.770113`, `DELTA = 0.05`, `KAPPA = 5`, `KAPPA_W = 0`, `B1 = 0.586418`, `B2 = 0.144796`, `WINDOW = 15`, `LOOKBACK_SEASONS = 3`, `AGES = 6`, and `TAG_MULTIPLIERS = {"IL": 0.3, "IL+": 0.3, "O": 0.6, "Q": 0.9, "GTD": 0.9, "DTD": 0.9, "SUSP": 0.7, "NA": 0.0}`;
  - `age_counts(played, team_games, missed, season_of, cut)`, ported from `analysis/availability.py: AvailabilityData.counts`;
  - `dab(counts)`, ported from `Fit.blend` with the constants;
  - `tag_multiplier(status)`.

  Make T017 pass.
- [X] T020 [US3] Create `backend/src/ffmodel/core/data/history.py` with `get_availability_history(conn, player_ids, as_of)`. It returns seasons (with final games ≤ `as_of`), per-player played dates, per-player team-game dates via `player_team_stint`, and inferred missed seasons. Missed seasons are a team's worth of evenly spaced game days of that season, with `known_from` = the first game after it. The SQL is restricted to the requested ids, as in `analysis/availability.py: load`. Export it from `backend/src/ffmodel/core/data/__init__.py`, and register it in `backend/tests/contract/test_offline_reads.py` (the readers list plus an offline call on the fixture).
- [X] T021 [US3] Create `backend/src/ffmodel/tools/impact_analysis/fragility.py` with `apply(option, projections, scenario, statuses, conn, as_of)` → projections with availability replaced per data-model.md's table. Use `dataclasses.replace`; unprojected stay unprojected. dAB results are cached per (database URL, as-of, load run) in `cache.py`, extended on demand for new player ids.
- [X] T022 [US3] In `backend/src/ffmodel/tools/impact_analysis/analysis.py`, apply `fragility.apply(s.fragility, ...)` to the projections right after `cache.projections` (before `_roster_rows`, `_compute` and xLift). Statuses come from `state.info`. In `picker.py`, apply it to the pool projections (replacing T009's interim Last 15). Echo `fragility` in `_settings_echo`.
- [X] T023 [US3] In `backend/src/ffmodel/api/schemas.py`, add `fragility: Literal["none", "last15", "dab", "dab_tag"] = "dab_tag"` to `ScenarioRequest`, and to `SettingsEcho`. Pass it through in `backend/src/ffmodel/api/routes.py` where `AnalysisSettings` is built.
- [X] T024 [P] [US3] Frontend:
  - add `fragility: "none" | "last15" | "dab" | "dab_tag"` (default `"dab_tag"`) to `Settings` in `frontend/src/state/scenario.ts`, with a `setFragility` action, sent in requests by `frontend/src/App.tsx`;
  - bump `STORAGE_KEY` to `"ffm.impact.v3"` (research R9) and update the key in `frontend/tests/*.test.tsx`;
  - add the **Fragility Penalty** dropdown (None, Last 15, dAB, dAB × tag) to `frontend/src/components/Controls.tsx`;
  - add the **Fragility Penalty** help entry in `frontend/src/help/content.ts` with contracts/ui.md's wording (no file names).
- [X] T025 [US3] Run `uv run pytest -q` and `npm test`. All pass.

**Checkpoint**: fragility options work end to end.

---

## Phase 6: User Story 4 - The opponent's roster in tactical mode (P3)

**Goal**: the opponent's rows show xLift for the opponent; the selected team's rows and the
picker keep the selected team's (FR-011, FR-018).

**Independent Test**: in the tactical fixture, the opponent's roster has exactly one active
player at 0, its weakest, and those values differ from scoring the same players for the
selected team.

- [X] T026 [P] [US4] In `backend/tests/integration/test_xlift_rows.py`, add a tactical test on `impact_engine` with a matchup state loaded (as in `tests/integration/test_impact_tactical.py`):
  - the opponent's roster rows carry `xlift`, with its weakest active player at 0;
  - picker values are for the selected team;
  - the tactical matchup odds are unchanged between `fragility="none"` and `"dab"` (FR-018: the fragility option affects only xLift in tactical mode).
- [X] T027 [US4] Confirm that `analysis.py` computes `score_rows` and the spread in tactical mode too, using the strategic-style spread from `cache.spread` (research R2). Fix anything T026 exposes.

---

## Phase 7: Polish & cross-cutting

- [X] T028 [P] Create `analysis/xlift_parity.py` (research R10).
  - **SC-001:** for team 1 at today's as-of, run the app path (`analyze` and `list_players` with `fragility="last15"`, window 82, games per period 3) and the rankings notebook (`player_rankings_analysis.app.run()`). With the notebook's defaults (after T031): weakest-player swap, weekly curve, window availability. Print the max |Δ xLift| over free agents; PASS ≤ 0.05.
  - **SC-005:** compare app dAB (via `fragility.apply` with `"dab"`) against `availability.py` (`av.fit(av.backtest(av.load(...))).fit.blend(...)`) for all rostered players; PASS ≤ 0.001.

  Exit nonzero on FAIL.
- [X] T029 Run, after T028 and T031, `cd analysis && uv run python xlift_parity.py`. Both PASS. If SC-001 fails, compare spreads and weakest-player choices first; if SC-005 fails, compare the age counts.
- [X] T030 [P] Update `docs/tool1-impact-analysis.md` with the domain rules: what xLift measures (the baseline is the weakest active player, scored for the team shown) and the four Fragility Penalty options (the default is dAB × tag; dAB in plain words). Update `specs/002-impact-analysis/research.md` with a short pointer to 007.
- [X] T031 In `analysis/player_rankings_analysis.py`, change the *Swap out* default from "Average rostered player" to "Team's weakest player", to match the app. Change the weekly-noise cell to simulate from the shrunk projections (the same ones the rankings use when *Shrink* is on), so its spreads match the app's (research R10). Add a caveat that the notebook's weekly spreads always use the window availability. Run `uv run marimo check` and `uv run marimo export html` on it.
- [X] T032 Run quickstart §5 (performance) on the real league: cold analysis ≤ 1.38 s and cold picker listing < 1 s (SC-006). If either is over, profile before optimizing. Likely levers: the dAB reads (restrict to the requested ids, one query per table), spreads (cached), and picker projections (reuse the 006 pool windows).
- [X] T033 Run the full gates: `uv run pytest -q`, `uv run ruff check src tests`, `uv run ruff format --check src tests` and `uv run lint-imports` in `backend/`; `npm test` in `frontend/`; `npm run build` in `frontend/` (so `ffm serve` without `--reload` gets the new UI). All pass.

---

## Dependencies & execution order

- **Setup (T001–T002)** → **Foundational (T003–T007)** → stories.
- **US1 (T008–T013)** depends on Foundational. It's the MVP; it uses Last 15 availability until US3 lands.
- **US2 (T014–T016)** depends on Foundational. It's independent of US1, though both touch `schemas.py`, so do them in sequence.
- **US3 (T017–T025)** depends on Foundational. T022 depends on US1 (T009) and US2 (T015) existing, since it wires fragility into both.
- **US4 (T026–T027)** depends on US2 (roster scoring).
- **Polish**: T028–T029 need US1–US3; T030–T031 can run any time after US2; T032–T033 come last.

## Parallel opportunities

- T003 runs alongside T005–T007; T004 must exist before T005's scoring calls run.
- T011 and T012 (US1 frontend) run alongside T009 and T010 once the field name is fixed.
- T017 and T018 (US3 tests) together; then T019 and T020 (different files) together.
- T024 (frontend) runs alongside T019–T023.
- T026 runs alongside US3.
- T028 and T030 together; T031 before T029.

### Example: US3 in parallel

```text
T017 dAB unit tests        T018 fragility integration tests
T019 core/model/availability.py    T020 core/data/history.py
T024 frontend dropdown + help
```

## Implementation strategy

1. **MVP**: Setup → Foundational → US1. The picker ranks free agents by xLift, with Last 15
   availability.
2. **US2**: xLift on the roster.
3. **US3**: the Fragility Penalty and dAB in the app (default dAB × tag).
4. **US4**: confirm the tactical opponent's values.
5. **Polish**: parity with the notebook, docs, performance and gates.
