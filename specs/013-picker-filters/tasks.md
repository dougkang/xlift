# Tasks: Player Picker Filters and Category Sort

## Phase 1: Setup
- [x] T001 Baseline: backend and frontend suites pass

## Phase 2: Foundational
- [x] T002 Add `positions`, `owners`, `sort_categories` to `PlayersRequest` and `sort_xlift` to `PlayerRow` in `backend/src/ffmodel/api/schemas.py`; pass them through `impact_players` in `backend/src/ffmodel/api/routes.py`
- [x] T003 Add the keyword arguments to `list_players` in `backend/src/ffmodel/tools/impact_analysis/picker.py`, defaults empty (FR-010)

## Phase 3: US1 Position (P1)
- [x] T004 [US1] Filter candidates by position (any match) in `picker.py`
- [x] T005 [US1] Tests: C only centers; G+C any; no-position players only unfiltered, in `backend/tests/integration/test_picker_filters.py`

## Phase 4: US2 Team (P1)
- [x] T006 [US2] Filter by owner (`"fa"` or team id, scenario owners) in `picker.py`
- [x] T007 [US2] Tests: two teams; free agents; combined with position; moved player filtered by new owner, in `test_picker_filters.py`

## Phase 5: US3 Category sort (P1)
- [x] T008 [US3] With `sort_categories`: validate keys against the format (unknown → `ValueError` → 422), score by `score_pool_by_category`, rank by the summed value (free agents first, name tie-break), set `sort_xlift`; total xLift unchanged, in `picker.py` (map the error in `routes.py`)
- [x] T009 [US3] Tests: order by REB+BLK; equals Player Analysis breakdown sum (SC-003); TO direction; unknown key 422; default output identical (pre-009 snapshot still passes), in `test_picker_filters.py`

## Phase 6: Frontend
- [x] T010 Regenerate `frontend/src/api/schema.d.ts`
- [x] T011 Picker controls in `frontend/src/components/PlayerPicker.tsx`: Position pills (G/F/C), Team multi-select (Free agents + other teams, from the league), Sort by category pills; send with the request; reset page on change; drop teams no longer offered; "No players match" empty state; second column `xLift <CATS>` when sorting
- [x] T012 Styles for pills and the multi-select in `frontend/src/styles/base.css` (style guide controls)
- [x] T013 Frontend tests in `frontend/tests/picker-filters.test.tsx`: each control sends its field; sort column header; empty state

## Phase 7: Polish
- [x] T014 Help: the picker topic names Position, Team and Sort by, in `frontend/src/help/content.ts`
- [x] T015 Docs: `docs/tool1-impact-analysis.md` player picker section
- [x] T016 Full suites, lint, build

## Dependencies
T002–T003 before stories; US1–US3 backend independent (same file, sequential); frontend after T010.
