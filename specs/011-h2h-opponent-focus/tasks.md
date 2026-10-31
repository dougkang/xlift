# Tasks: Focus on an H2H Opponent

**Input**: Design documents from `/specs/011-h2h-opponent-focus/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: included. The constitution requires tool changes to be tested on fixture data, and
SC-001, SC-002, SC-005 are exact equalities that tests can pin.

## Phase 1: Setup

- [x] T001 Confirm the baseline: `cd backend && uv run pytest -q` and `cd frontend && npm test` pass on the branch before changes (the pre-010 regression pins unfocused output)

## Phase 2: Foundational (blocks every story)

- [x] T002 Add `focus_opponent_id: int | None = None` to `AnalysisSettings` and set it to `None` in `normalize()` when `mode != "strategic"` in `backend/src/ffmodel/tools/impact_analysis/settings.py`; echo it in `_settings_echo` in `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T003 Add `focus_opponent_id: int | None = None` to `ScenarioRequest`, `focus_opponent_id` to `SettingsEcho`, a `Focus` model (`opponent_id: int`, `opponent_name: str`) and `AnalysisResult.focus: Focus | None = None` in `backend/src/ffmodel/api/schemas.py`; pass the field through `_settings` in `backend/src/ffmodel/api/routes.py`
- [x] T004 Add `cache.computed(conn, settings, moves, compute)`: an LRU (8 entries) of `Computed` keyed by the original-cache key fields *without* `focus_opponent_id` plus `repr(tuple(moves))`, and add `focus_opponent_id` to the `original()` key, in `backend/src/ffmodel/tools/impact_analysis/cache.py`; clear both in `clear()`
- [x] T005 Route `_compute` calls in `_analyze` through `cache.computed` (the `reuse` path stays inside `compute`) in `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T006 Validate focus: in `ScenarioRequest` (`backend/src/ffmodel/api/schemas.py`) add a model validator rejecting `focus_opponent_id == team_id`, which FastAPI returns as 422 like other invalid settings; in `_analyze` raise `NotFound` for a `focus_opponent_id` not in the league, which `_run` in `backend/src/ffmodel/api/routes.py` already maps to 404
- [x] T007 [P] Unit test the cache: same settings and moves with different focus reuse one `Computed` (`compute` called once); different moves or settings miss, in `backend/tests/unit/test_computed_cache.py`

## Phase 3: User Story 1 — compare with one opponent (P1)

**Goal**: a focused response draws the matchup. **Independent test**: analyze with `focus_opponent_id` and check the focused fields.

- [x] T008 [US1] Compute matchup win rates: `_matchup_win_rate(values, me, opp, fmt)` → per category P(win) + ½·P(tie) for `me` vs `opp` (from `fmt.compare`, same as the H2H odds) in `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T009 [US1] Under focus (strategic): `result["focus"] = {"opponent_id", "opponent_name"}`; `radar.series` = opponent (`emphasis: "opponent"`) then selected, each `win_rate` replaced by the matchup chance (selected: mine; opponent: `1 - mine`), `ranks`/`normalized`/`area`/`averages` unchanged; `radar.league = []`, in `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T010 [US1] Under focus: `category_table.rows[i].league_average` = the opponent's projected average, `win_rate` = the selected team's matchup chance; Rank, Avg and Leader fields unchanged, in `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T011 [US1] Under focus: `_curves` takes the focused opponent; role `opponent` (label: the opponent's name, mean: its projected average) replaces `league_average`; `leader`/`next_best` kept unless its team is the opponent, in `backend/src/ffmodel/tools/impact_analysis/analysis.py`
- [x] T012 [US1] Integration tests in `backend/tests/integration/test_impact_focus.py`: two radar series; League column = opponent averages; Win % column = radar selected `win_rate` = H2H row odds P(win)+½P(tie) for that opponent (SC-001); opponent curve mean = League column value per category (SC-002); leader dropped when it is the opponent; `league_shape`, `matchups`, `matchup_totals`, `header`, `rosters` and the selected team's own fields (radar `ranks`, `normalized`, `area`, `averages`; table `rank`, `average`, leader fields) identical to the unfocused result, with only `win_rate` differing (SC-005); tactical ignores focus; unknown team 404, own team 422 via the API; API model validates
- [x] T013 [US1] Scenario state: `focusOpponentId: number | null` with a `setFocus` action (toggle: same id clears), cleared by `setLeague`, `setTeam`, `setMode`; excluded from session storage, in `frontend/src/state/scenario.ts`
- [x] T014 [US1] Send `focus_opponent_id` with analyze requests (strategic only) in `frontend/src/App.tsx` (and `frontend/src/api/client.ts` if the body is built there)
- [x] T015 [US1] Make H2H opponent rows clickable in both layouts: `onClick`/Enter/Space dispatch `setFocus`, `tabIndex={0}`, `aria-pressed`, the existing `opponent-row` class (yellow, `--yours`, the style guide's "selected rows") on the focused row, in `frontend/src/components/RecordTable.tsx` and `frontend/src/styles/base.css`
- [x] T016 [US1] Labels under `result.focus`: the League header shows the opponent's name (shortened, full name in `title`) in `frontend/src/components/CategoryTable.tsx`; the radar legend names the opponent in `frontend/src/components/Radar.tsx`; the curve legend uses the series label for `opponent` in `frontend/src/components/CategoryCurves.tsx`
- [x] T017 [US1] Regenerate `frontend/src/api/schema.d.ts`; export a focused fixture `strategic_focus.json` in `backend/tests/fixtures/export_frontend_fixtures.py` (only the new file is kept)
- [x] T018 [US1] Frontend tests in `frontend/tests/focus.test.tsx`: clicking a row sends `focus_opponent_id` and marks the row; with the focused fixture the radar has two shapes, the League header is the opponent's name, curves show the opponent

## Phase 4: User Story 2 — return to the league view (P1)

**Independent test**: clear focus and get the unfocused page back.

- [x] T019 [US2] Frontend tests in `frontend/tests/focus.test.tsx`: clicking the focused row again sends no focus; clicking another row moves it; changing mode, team or league clears it; keyboard Enter toggles
- [x] T020 [US2] Integration test: the unfocused result after a focused one equals a fresh unfocused result (SC-004) in `backend/tests/integration/test_impact_focus.py`

## Phase 5: User Story 3 — keep focus while testing moves (P2)

**Independent test**: focus, make a move, check focus and the before markers stay.

- [x] T021 [US3] Under focus in `backend/src/ffmodel/tools/impact_analysis/changes.py`: include the opponent in `radar.original`/`tones` when its active players changed (as tactical does); the `league_average` change uses the inverse direction (`_inverse(cat)`)
- [x] T022 [US3] Integration tests in `backend/tests/integration/test_impact_focus.py`: with a move, focused changes exist and the selected team's `(before)` curve is present; a trade with the focused opponent changes their radar shape, League column and curve and includes them in `radar.original`; a focus change after a move doesn't re-simulate (count `_compute` calls)
- [x] T023 [US3] Frontend test: focus stays after `addMove`, `popMove`, `reset`, `setWindow`, `setFragility` and `setRadarScale` in `frontend/tests/focus.test.tsx`

## Phase 6: Polish

- [x] T024 Help: H2H says clicking a row focuses on that opponent and clicking again returns; radar, Per Category Ranking and Category Breakdown say what changes under focus (Win % becomes your chance against them); within 120 words, no file names, in `frontend/src/help/content.ts`
- [x] T025 [P] Docs: describe focus in `docs/tool1-impact-analysis.md`
- [x] T026 Measure a focus click on the real league (warm): `focus_opponent_id` request time ≤ 0.5 s (SC-003); record the number in `specs/011-h2h-opponent-focus/research.md`
- [x] T027 Run the full suites: `uv run pytest -q`, `uv run lint-imports`, `uv run ruff check .`, `npx tsc -b`, `npm test`, `npm run build`

## Dependencies

- Phase 2 blocks all stories. T004 → T005; T002–T003 before T006.
- US1 backend (T008–T012) before US1 frontend fixture (T017) and tests (T018).
- US2 needs US1's state and rows (T013–T015). US3 needs US1 backend.
- T024–T027 last.

## Parallel examples

- T007 alongside T008–T011 (different files).
- T013–T016 (frontend) alongside T012 (backend tests) once T009–T011 land.
- T025 any time.

## Implementation strategy

MVP: Phases 1–3 (focus a row, see the matchup). Then US2 (leaving focus, mostly frontend), US3
(changes with moves), polish.
