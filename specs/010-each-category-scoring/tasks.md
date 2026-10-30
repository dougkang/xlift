# Tasks: H2H Each-Category Scoring

**Input**: Design documents from `/specs/010-each-category-scoring/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: required by the constitution's quality gates (outcome logic with ties, both modes,
format conformance) and by SC-004 (most-categories unchanged).

## Phase 1: Setup

- [x] T001 Record the pre-010 snapshot: add `tests/integration/test_pre010_snapshot.py` (marked `snapshot`) that writes full strategic and tactical analysis results, with and without one move, for the fixture league to `backend/tests/fixtures/pre010_impact.json`; run it once on the unchanged code (research R7)

## Phase 2: Foundational (blocks every story)

- [x] T002 Add `standings: Literal["matchup", "category"] = "matchup"` to `ScoringFormat` in `backend/src/ffmodel/core/scoring/base.py`
- [x] T003 Register `9cat_h2h_each` ("9-category head-to-head, each category", `standings="category"`) via `dataclasses.replace(NINE_CAT_H2H, ...)` in `backend/src/ffmodel/core/scoring/nine_cat.py`
- [x] T004 Add `ExpectedRecord` (wins, losses, ties floats; `win_pct` = (W + ½T) ÷ (W + L + T), 0 when total is 0; `__add__`) and `expected_record(odds)` to `backend/src/ffmodel/core/sim/engine.py`, export from `backend/src/ffmodel/core/sim/__init__.py`
- [x] T005 [P] Conformance: assert every format declares a valid `standings` and that `9cat_h2h_each` shares `9cat_h2h`'s categories in `backend/tests/scoring/test_conformance.py`
- [x] T006 [P] Unit tests for `expected_record`: sums, ties counted ½ in `win_pct`, per-opponent total = categories, addition, empty in `backend/tests/unit/test_engine.py`
- [x] T007 Add `standings` to every analysis result and the additive API models (`ExpectedRecordModel`, `Header.expected_record`, nullable `RecordModel`/`result`/`matchups`, `MatchupTotals.expected`, `HeaderChange.expected_wins`/`win_pct`, `MatchupChange.expected_wins` with nullable `original_result`/`transition`, `TotalsChange.expected_wins` with nullable `matchups`) in `backend/src/ffmodel/tools/impact_analysis/analysis.py` and `backend/src/ffmodel/api/schemas.py` per contracts/api.md
- [x] T008 Add `backend/tests/integration/test_pre010_regression.py`: most-categories results equal `pre010_impact.json` with the new keys removed (SC-004)

## Phase 3: User Story 1 — strategic category record (P1)

**Independent test**: each-category league, Strategic: headline = summed expected record with win %.

- [x] T009 [US1] Under `fmt.standings == "category"`, set `header.expected_record` (summed over opponents, unrounded) and `header.record = None` in the strategic path of `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T010 [US1] Integration tests in `backend/tests/integration/test_impact_each_category.py`: headline win % equals the mean radar Win % of the selected team within 0.005 (SC-001); W+L+T = 9 × opponents; `standings == "category"`; API validates
- [x] T011 [US1] Strategic headline under `standings === "category"`: "Category Record", W–L–T to one decimal, win % in `frontend/src/components/RecordHeadline.tsx`, with a `formatRecord` helper in `frontend/src/format.ts`

## Phase 4: User Story 2 — changes from moves (P1)

**Independent test**: a move shows a signed expected-wins change to one decimal.

- [x] T012 [US2] In `backend/src/ffmodel/tools/impact_analysis/changes.py`: `EXPECTED_DECIMALS = 1`; under the category rule fill `header.expected_wins` (both modes), `header.win_pct` (strategic, whole points), row and totals `expected_wins`; null flips/original results and W/L/T changes; matchup rule unchanged
- [x] T013 [P] [US2] Unit tests for the category-rule change builder (0.04 → no change, 0.06 → +0.1, tones) in `backend/tests/unit/test_changes.py`; integration test with a move in `backend/tests/integration/test_impact_each_category.py`
- [x] T014 [US2] Show `expected_wins` (and `win_pct`) changes in the headline in `frontend/src/components/RecordHeadline.tsx`

## Phase 5: User Story 3 — tactical projected record (P2)

**Independent test**: tactical each-category headline = this week's expected record.

- [x] T015 [US3] Under the category rule set `header.expected_record` from the current matchup's per-category odds and `header.record = None` in `_tactical_results` in `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T016 [US3] Integration test: tactical expected record sums to 9; a final week equals the current score, in `backend/tests/integration/test_impact_each_category.py`
- [x] T017 [US3] Tactical headline "Projected Record" with its change in `frontend/src/components/RecordHeadline.tsx`

## Phase 6: User Story 4 — H2H table (P2)

**Independent test**: each-category H2H shows Record and Win % per opponent; Total = headline.

- [x] T018 [US4] Under the category rule: rows' `expected_record`, `result = None`; `matchup_totals.expected` (sum), `matchups = None` in `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T019 [US4] Integration test: Total equals the headline (SC-005), rows have no result, in `backend/tests/integration/test_impact_each_category.py`
- [x] T020 [US4] H2H table under the category rule: Opponent | Record | Win %, Total row, row changes, no Result column in `frontend/src/components/RecordTable.tsx`

## Phase 7: User Story 5 — set the league's rule (P2)

- [x] T021 [US5] Validate `--format` against `available_formats()` in `ffm load roster`, exit 1 listing known formats, in `backend/src/ffmodel/cli.py`
- [x] T022 [US5] Test: unknown format refused; a later load without `--format` keeps `9cat_h2h_each`, in `backend/tests/integration/test_roster_loader.py`

## Phase 8: Polish

- [x] T023 Help: `headline` and `h2h` topics explain the rule in force (category: every category is a W/L/T, expected values, ties ½); add `standings` to the help context in `frontend/src/help/content.ts` and its callers (`frontend/src/App.tsx`); no file names
- [x] T024 Regenerate `frontend/src/api/schema.d.ts` from the OpenAPI schema
- [x] T025 Export each-category fixtures (`strategic_each.json`, `tactical_each.json`, `strategic_each_moves.json`) in `backend/tests/fixtures/export_frontend_fixtures.py`; add `frontend/tests/each-category.test.tsx` (headline, H2H, tactical, changes, help)
- [x] T026 [P] Docs: both rules, the league's rule, revised strategy notes in `docs/overview.md` and `docs/tool1-impact-analysis.md`
- [x] T027 Run the full backend (`uv run pytest`, `uv run lint-imports`, ruff) and frontend (`npm test`, `npx tsc -b`) suites

## Dependencies

- T001 before any code change. Phase 2 blocks all stories.
- US1 → US2 (changes need the headline fields); US4's change rows depend on T012.
- US3, US4, US5 independent of each other after Phase 2.
- T024 after all schema changes; T025 after T024.

## Parallel examples

- T005, T006 together after T002–T004.
- T021–T022 (CLI) alongside US3/US4.
- T026 (docs) any time.

## Implementation strategy

MVP: Phases 1–3 (the strategic headline). Then US2 (changes), US4 (H2H), US3 (tactical), US5,
polish.
