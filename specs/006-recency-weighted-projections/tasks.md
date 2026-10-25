---

description: "Task list for 006 recency-weighted player projections"
---

# Tasks: Recency-Weighted Player Projections

**Input**: Design documents from `/specs/006-recency-weighted-projections/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: included. The constitution's quality gates require automated tests for core changes,
and plan research R8 lists them.

**Organization**: tasks are grouped by user story (spec.md) so each can be implemented and
verified on its own.

**Starting point**: the working tree holds an uncommitted pre-spec draft (plan.md,
*Implementation status*). Tasks marked *(draft exists)* mean: review the draft against the
requirement cited, correct it, and complete it. They don't mean rewrite from scratch. Don't touch
`docs/overview.md` or `docs/tool2-player-comparison.md`; they're the user's own uncommitted
edits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story the task belongs to (US1–US4)

---

## Phase 1: Setup

**Purpose**: confirm the baseline the feature builds on

- [X] T001 Run `uv run pytest -q`, `uv run ruff check src tests` and `uv run lint-imports` in `backend/`. Record the current result: the draft is expected to fail only `tests/integration/test_impact_strategic.py::test_short_history_footnote` and `tests/integration/test_api_moves_players.py::test_free_agents_only_and_footnote`, both on "* N of 82 games". Note any other failure before starting.
- [X] T002 Confirm the real database (`data/ffmodel.sqlite`) has regular-season games for 2022-23 through the current season, which quickstart §2 and the backtest need: `sqlite3 data/ffmodel.sqlite "select season_id, count(*) from game where season_type='regular' and status='final' group by 1"`.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: interface additions that US1 and US2 both build on

- [X] T003 Add `unshrunk_stats: tuple[str, ...] = ()` to `ScoringFormat` in `backend/src/ffmodel/core/scoring/base.py`, with a field comment ("base stats whose per-game means aren't shrunk toward the typical player"), per contracts/scoring-format.md.
- [X] T004 Set `unshrunk_stats=("blk",)` in `NINE_CAT_H2H` in `backend/src/ffmodel/core/scoring/nine_cat.py`.
- [X] T005 [P] Add a conformance assertion in `backend/tests/scoring/test_conformance.py`: every name in `fmt.unshrunk_stats` is in `fmt.base_stats`, for every registered format.
- [X] T006 In `backend/src/ffmodel/core/model/fit.py` *(draft exists)*, confirm `PlayerProjection` has `effective_games: float | None = None` and the `n_eff` property ("`effective_games`, or `games_found` when None"). Also confirm the module constants `RECENCY_HALF_LIFE = 40.0` and `SEASON_WEIGHT = 0.25`, each with a comment citing research R1.

**Checkpoint**: the interface is ready, and the full suite is no worse than T001's baseline.

---

## Phase 3: User Story 1 - Projections follow current form without overreacting (P1) 🎯 MVP

**Goal**: per-game fits use recency weights over up to *X* games, with effective games driving
every sample-size calculation (FR-001–FR-005).

**Independent Test**: unit tests on hand-built windows, plus quickstart §2's SC-001/SC-002 lines.

### Tests for User Story 1

- [X] T007 [P] [US1] In `backend/tests/unit/test_projection.py`, add a test that `fit_projection(..., half_life=None, season_weight=1.0)` gives the same mean, `chol @ chol.T` and `mean_stderr` as today's equal-weight formula on the existing 3-game window, with `effective_games == 3` (FR-003).
- [X] T008 [P] [US1] In `backend/tests/unit/test_projection.py`, add a test for a 4-game, two-season window with `half_life=40, season_weight=0.25, season="2026-27"`. Hand-compute the weights 0.5^(j/40) × 0.25^age, then check the weighted mean, the reliability-weighted covariance Σw(x−μ)(x−μ)ᵀ/(Σw − Σw²/Σw), `effective_games = (Σw)²/Σw²`, λ = 5/(n_eff − 1 + 5) and `mean_stderr = sqrt(diag Σ / n_eff)` (FR-002–FR-004).
- [X] T009 [P] [US1] In `backend/tests/unit/test_projection.py`, add a test that a game two seasons before `season` (a missed season in between) weighs `0.25**2` of an otherwise identical current-season game (spec edge case; research R1).
- [X] T010 [P] [US1] In `backend/tests/unit/test_projection.py`, add a test that `fit_projection` orders games most recent first by `(game_date, game_id)` whatever the input order, so that weights follow recency.

### Implementation for User Story 1

- [X] T011 [US1] In `backend/src/ffmodel/core/model/fit.py` *(draft exists)*, finalize `fit_projection(player_id, window, base_stats, *, shrink_k, half_life=None, season_weight=1.0, season=None)`. It computes the weights, the weighted mean and covariance, n_eff, λ and stderr per T007–T010, and returns `effective_games`. Keep the zero-games path unchanged: `chol=None`, zero mean.
- [X] T012 [US1] In `backend/src/ffmodel/core/model/projection.py` *(draft exists)*, finalize `_fit(pid, window, fmt, as_of)` so it calls `fit_projection` with `half_life=RECENCY_HALF_LIFE`, `season_weight=SEASON_WEIGHT` and `season=current_season(as_of)` (from `ffmodel.contract.seasons`). Use it in both `build_prior` and `build_projections`.
- [X] T013 [US1] Run `uv run pytest -q tests/unit/test_projection.py` and `uv run lint-imports` in `backend/`. All pass, and the layering contracts are kept (core importing `contract.seasons` is allowed).

**Checkpoint**: US1 delivers weighted projections; shrinkage behaves as in the draft.

---

## Phase 4: User Story 2 - Small samples are pulled toward a typical player (P1)

**Goal**: empirical-Bayes mean shrinkage on effective games, with the blocks exemption coming
from the format (FR-006–FR-012).

**Independent Test**: unit tests on synthetic pools; integration wiring through
`build_projections`; quickstart §2's SC-003/SC-007 lines.

### Tests for User Story 2

- [X] T014 [P] [US2] In `backend/tests/unit/test_projection.py`, add a test that `estimate_prior(..., exempt=[i])` records `exempt == (i,)` and that `shrink_projection` leaves `mean[i]` equal to the unshrunk mean while shrinking the other stats (FR-009).
- [X] T015 [P] [US2] In `backend/tests/unit/test_projection.py`, add tests that `estimate_prior`'s ratio makes and attempts and `shrink_projection`'s rate formula use `n_eff` (`effective_games`) rather than `games_found`: build projections with `effective_games` ≠ `games_found` and check *κ* and the shrunk rate (FR-008, research R2).
- [X] T016 [P] [US2] Confirm the existing tests in `backend/tests/unit/test_projection.py` still cover "no prior below 30 qualifying players", "pool needs ≥ 5 games" and the 3PM ≤ FGM cap after shrinkage (FR-010, FR-011). Extend them if a case is missing.
- [X] T017 [P] [US2] In `backend/tests/integration/test_projection_db.py`, add a test that `build_prior` on a format whose `unshrunk_stats` names a stat yields `MeanPrior.exempt` containing its index. Use a fixture pool large enough for a prior, or a constructed prior passed through `build_projections(prior=...)` if the fixture is too small (FR-009, research R4).

### Implementation for User Story 2

- [X] T018 [US2] In `backend/src/ffmodel/core/model/fit.py` *(draft exists)*, finalize `MeanPrior.exempt: tuple[int, ...] = ()` and `estimate_prior(fits, ratio_pairs=(), caps=(), exempt=())`. The pool is `games_found >= PRIOR_MIN_GAMES`; return `None` below `PRIOR_MIN_POOL`; ratio totals use `n_eff`. In `shrink_projection`, restore exempt means after the counting-stat step and use `n_eff` for ratio totals.
- [X] T019 [US2] In `backend/src/ffmodel/core/model/projection.py`, remove the draft's `UNSHRUNK_STATS` constant. Make `build_prior` derive `exempt = [idx[s] for s in fmt.unshrunk_stats if s in idx]` and pass it to `estimate_prior` (research R4, Principle II).
- [X] T020 [US2] In `backend/src/ffmodel/tools/impact_analysis/cache.py` *(draft exists)*, confirm the prior is built once per projection-cache key, evicted with its bucket and cleared by `clear()` (FR-012, research R7).
- [X] T021 [US2] Run `uv run pytest -q tests/unit tests/integration/test_projection_db.py` in `backend/`. All pass.

**Checkpoint**: US1 and US2 together match the spec's model.

---

## Phase 5: User Story 3 - The games setting means "how far back" (P2)

**Goal**: the default lookback is 82, the help explains the new meaning, and the footnote keeps
its rule (FR-001, FR-014, FR-015).

**Independent Test**: load the app with defaults and check the input, the help and a short-history
footnote (quickstart §5); the API tests' echoed `settings.window`.

- [X] T022 [P] [US3] Confirm `DEFAULT_WINDOW = 82` (with its comment) in `backend/src/ffmodel/tools/impact_analysis/settings.py` and `window: int = Field(82, ge=1, le=82)` in `backend/src/ffmodel/api/schemas.py` *(draft exists)*, per contracts/api.md.
- [X] T023 [P] [US3] Confirm `window: 82` in the initial settings in `frontend/src/state/scenario.ts` *(draft exists)*.
- [X] T024 [P] [US3] Replace the "Last X games" help line in `frontend/src/help/content.ts` with contracts/ui.md's wording: "the most games each projection draws on (now ${ctx.window}); recent games count more, and last season's count less. Small samples are pulled toward a typical player." Change only that line and keep the file's existing formatting (no Prettier pass over the file).
- [X] T025 [US3] Update the footnote expectations in `backend/tests/integration/test_impact_strategic.py` (`test_short_history_footnote`) and `backend/tests/integration/test_api_moves_players.py` (`test_free_agents_only_and_footnote`) to the new default. Each should assert the rule (games found < window), not just the literal string, e.g. "* 2 of 82 games" for the rookie. Add `window=15` cases if an existing test's intent was the 15-game behavior.
- [X] T026 [US3] Run `npm test` in `frontend/`, and `uv run pytest -q tests/integration` in `backend/`. All pass.

**Checkpoint**: the setting reads correctly end to end.

---

## Phase 6: User Story 4 - Availability is unchanged (P3)

**Goal**: availability stays the most-recent-15-games estimate whatever the lookback (FR-013,
SC-004).

**Independent Test**: availability at window 15 and window 82 is identical for every player
(fixture test plus quickstart §3).

- [X] T027 [P] [US4] In `backend/tests/integration/test_projection_db.py`, add a test that for the fixture players (`fx.IGGY`, `fx.DONCIC`, `fx.DYBANTSA`), `build_projections(..., window=82, prior=None)` gives the same `availability` as `window=15`, including IGGY's 0.5 and the short-history stint rule for DYBANTSA.
- [X] T028 [US4] In `backend/src/ffmodel/core/model/projection.py` *(draft exists)*, confirm availability uses the most recent `AVAILABILITY_GAMES = 15` games of the window. Its start is the earliest of those games, extended back to the first stint only when the player has fewer than 15 games in total. The rate is `availability_rate(len(recent), team_games)` (research R5).
- [X] T029 [US4] Run quickstart §3 against the real database and confirm `identical availability: True`.

**Checkpoint**: all four stories complete.

---

## Phase 7: Polish & cross-cutting

- [X] T030 [P] Create `analysis/projection_backtest.py`, the reproducible instrument for SC-001, SC-002, SC-003 and SC-007 (research R9). It:
  - loads game logs with `analysis/minutes.py` (`mn.load`);
  - builds early- and mid-season cutoffs as in `mn.backtest`;
  - fits with the **backend's** `fit_projection` (window 15 equal weights vs. weighted with `RECENCY_HALF_LIFE` / `SEASON_WEIGHT` over 82 games);
  - shrinks with `estimate_prior` / `shrink_projection`, with the prior per cutoff from players with a game in the prior 365 days and `exempt` from `fmt.unshrunk_stats`;
  - prints one line per criterion with its value, threshold and PASS/FAIL:
    - SC-001: counting-stat MSE reduction, next 15, all cutoffs, ≥ 20%;
    - SC-002: next 30 and 60, early cutoffs, ≥ 20%;
    - SC-003: mean (projected − actual) points for 20+ point projections, next 15, within ±0.5;
    - SC-007: attempt-weighted FG% and FT% MSE reduction vs. the unshrunk weighted fit, next 15, ≥ 10%.
- [X] T031 Run `cd analysis && uv run python projection_backtest.py`. Every criterion must PASS. Record the values in `specs/006-recency-weighted-projections/quickstart.md`'s table if they differ from the reference values.
- [X] T032 [P] Update `docs/tool1-impact-analysis.md` *(draft paragraph exists)*. The domain rule should say: projections draw on up to X games, recent games count more and older seasons less, small samples are pulled toward a typical player, blocks excepted, and availability still reflects the most recent 15 games (FR-016).
- [X] T033 [P] Update the R1 addendum in `specs/002-impact-analysis/research.md` *(draft exists)* to cover the weighting (half-life 40, season weight 0.25, effective games), shrinkage on effective games, and the blocks exemption from `ScoringFormat.unshrunk_stats`, with a pointer to `specs/006-recency-weighted-projections/research.md` (FR-016).
- [X] T034 [P] In `analysis/player_rankings_analysis.py`, change the *Games window* slider default from 15 to 82 so the rankings (xLift) notebook matches the app. Its projections come from `build_projections`, so they're already weighted. Run `uv run marimo check` and `uv run marimo export html` on it to confirm it runs.
- [X] T035 Run quickstart §4 (performance): cold analysis time ≤ 1.5× the recorded 0.75–0.92 s baseline (SC-006). If it's exceeded, profile `build_prior` and the 82-game bulk query before changing anything.
- [X] T036 Run the full gates: `uv run pytest -q`, `uv run ruff check src tests`, `uv run ruff format --check src tests` and `uv run lint-imports` in `backend/`; `npm test` in `frontend/`. All pass. SC-005 (determinism) is covered by the existing seed tests passing at the new default.

---

## Dependencies & execution order

- **Setup (T001–T002)** → **Foundational (T003–T006)** → user stories.
- **US1 (T007–T013)** has no dependency on other stories. It's the MVP.
- **US2 (T014–T021)** depends on T003–T006 (format field, `n_eff`). It's independent of US1's tests, but shares `fit.py` and `projection.py`, so run it after US1 to avoid conflicting edits.
- **US3 (T022–T026)** is independent of US1 and US2 in code. T025's expected footnotes depend only on the window default.
- **US4 (T027–T029)** is independent; it touches `projection.py` (availability block), so run it after US2.
- **Polish**: T030–T031 need US1 and US2; T032–T034 can run any time after US2; T035–T036 come last.

## Parallel opportunities

- T005 runs alongside T003–T004 once the field name is fixed.
- T007–T010 (US1 tests) are all [P]: same file, independent test functions, so write them together.
- T014–T017 (US2 tests) are [P].
- T022, T023 and T024 (US3) touch different files: [P].
- T027 (US4 test) runs alongside US3.
- T032, T033 and T034 (docs and notebook) are [P].

### Example: US1 tests together

```text
T007 equal-weight reduction test
T008 hand-computed weighted test
T009 season-age / missed-season test
T010 recency ordering test
```

## Implementation strategy

1. **MVP**: Setup → Foundational → US1. Projections are recency-weighted, and the draft
   shrinkage works unchanged. Check SC-001/SC-002 with T030 early if useful.
2. **Add US2**: the shrinkage on effective games, with the exemption in the format (resolves
   the Principle II issue).
3. **Add US3**: the default and help, and the footnote tests go green.
4. **Add US4**: lock availability in with tests.
5. **Polish**: the backtest instrument, docs, notebook default, performance and full gates.
