---

description: "Task list for 008 League Shape Charts in the Category Breakdown"
---

# Tasks: League Shape Charts in the Category Breakdown

**Input**: Design documents from `/specs/008-league-shape-charts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: included. The constitution's quality gates require core tests, and the plan lists
them.

**Organization**: tasks are grouped by user story (spec.md). The core computation and the API
field are Foundational, because League shape (US1) and Against null (US2) both use them. The
before marker (US3) builds on US1. Don't touch `docs/overview.md` or
`docs/tool2-player-comparison.md`; they're the user's own uncommitted edits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US3 per spec.md

---

## Phase 1: Setup

- [X] T001 Create the feature branch from the current tip of `007-xwcwa-fragility-penalty`: `git switch -c 008-league-shape-charts`. Confirm the baseline: `uv run pytest -q` in `backend/` and `npm test` in `frontend/` pass before any change.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the DB-free core computation and the API field that every story reads

- [X] T002 [P] In `backend/tests/unit/test_league_shape.py`, write DB-free tests for T003, using `get_format("9cat_h2h")` and synthetic per-team averages for 6 teams. Cover:
  - places run 1…N in order of the competition rank `ranks(averages, fmt)`, with ties broken by team id; `rank` equals the competition rank;
  - TO is direction-aware: the fewest turnovers is place 1, and values rise with place;
  - a team with a NaN value in a category is omitted from that category, and N counts only teams with values;
  - gaps: `gap_r = |v_r − v_{r+1}|` ≥ 0, N − 1 of them;
  - null gaps equal the rankings report's formula on the same values (copied from the rankings notebook's gap cell): `z = [NormalDist().inv_cdf((i − 0.375)/(n + 0.25)) for i in range(n, 0, -1)]`, `(z[:-1] − z[1:]) * np.std(values, ddof=1)`, within 1e-9 (SC-003);
  - fewer than 3 teams with values gives no gaps;
  - all-equal values give gaps and null gaps of 0.
- [X] T003 Create `backend/src/ffmodel/core/sim/shape.py` (DB-free, research R2 and R3) with `league_shape(averages: Mapping[int, np.ndarray], fmt) -> list[dict]`. It returns one entry per category in `fmt.categories` order: `{"teams": [(team_id, place, rank, value)…], "gaps": [(to_place, gap, null_gap)…]}`, where `gaps` is empty when fewer than 3 teams have a value. Use `ranks` from `core/sim/engine.py` for `rank`. Export it from `backend/src/ffmodel/core/sim/__init__.py`. Make T002 pass.
- [X] T004 In `backend/src/ffmodel/api/schemas.py`, add Pydantic models per data-model.md:
  - `ShapeTeam` (team_id, team_name, place, rank, value, selected);
  - `ShapeGap` (to_place, gap, null_gap, `mark: Literal["climb", "cushion"] | None`);
  - `ShapePoint` (place, rank, value);
  - `CategoryShape` (category, teams, gaps, `before: ShapePoint | None`).

  Add `league_shape: list[CategoryShape] | None = None` to `AnalysisResult`.
- [X] T005 In `backend/src/ffmodel/tools/impact_analysis/analysis.py`, add `_league_shape(fmt, comp, names, selected, reuse)`. It turns `league_shape(comp.averages, fmt)` into the contract dicts, adding:
  - `team_name`;
  - `selected` (exactly one `true` when the selected team has a value);
  - gap marks (`"climb"` where `to_place == selected place − 1`, `"cushion"` where `to_place == selected place`);
  - `before`, null for now (T014 fills it).

  Set `result["league_shape"]` in the strategic branch of `_analyze`. Initialize it to `None` in the result dict, so tactical, unsupported-format and no-simulation results carry `null`.
- [X] T006 [P] In `backend/tests/integration/test_impact_shape.py`, write integration tests on `impact_engine` (as in `tests/integration/test_impact_strategic.py`):
  - strategic: `league_shape` has one entry per category, in `categories` order;
  - each category's `teams[i]["place"] == i + 1`, and each `rank` equals that team's rank in `radar.series[].ranks`; the selected team's also equals the `category_table` rank (SC-002);
  - each `value` equals the radar's `averages` for that team and category;
  - exactly one `selected` team per category, and at most one `climb` and one `cushion`, with places as in data-model.md;
  - the first-placed selected team has no climb; a last-placed one has no cushion (check over categories and teams);
  - tactical (with `fx.load_matchup_state`) gives `league_shape is None` (FR-015, SC-006);
  - the API response validates against `AnalysisResult`.
- [X] T007 Regenerate `frontend/src/api/schema.d.ts` from the app's OpenAPI. If `ffm serve` isn't running, dump `create_app(...).openapi()` and run `npx openapi-typescript <file> -o src/api/schema.d.ts`. Add `league_shape` to `frontend/tests/fixtures/strategic*.json` from a fresh export: run `tests/fixtures/export_frontend_fixtures.py` to a temp dir and copy only `league_shape` across, keeping every other field. Set `"league_shape": null` in `tactical*.json`.

**Checkpoint**: `uv run pytest -q tests/unit/test_league_shape.py tests/integration/test_impact_shape.py` passes; the full suite and `npm test` stay green.

---

## Phase 3: User Story 1 - See where my team sits in each category's league shape (P1) 🎯 MVP

**Goal**: each strategic category shows League shape with the selected team's dot marked (FR-001–FR-003, FR-006, FR-008).

**Independent Test**: render the strategic fixture; each of the 9 category blocks has a League shape chart with one point per team and one point marked as selected.

- [X] T008 [P] [US1] In `frontend/tests/league-shape.test.tsx`, test with the strategic fixture (as `frontend/tests/strategic.test.tsx` renders `App`):
  - every category block contains a League shape chart (`data-testid="league-shape"`) with one point per team in `league_shape[c].teams`;
  - exactly one point carries `data-selected="true"`, and its title text includes the selected team's name and rank;
  - with the tactical fixture, no League shape chart renders.
- [X] T009 [US1] Create `frontend/src/components/LeagueShape.tsx` with `LeagueShapeChart({ shape, decimals, width })` (contracts/ui.md, research R7). Hand-drawn SVG with `d3-scale` (as in `Radar.tsx`):
  - x = `place` (1 at the left, domain [1, N]), y = `value` (not zero-based), minimal ticks;
  - a `<polyline>` in light secondary (`#F5C1A9`) through all teams by place;
  - one `<circle>` per team with `data-team={team_id}`: other teams in `#CE7955`; the selected team in `--sel` (`#1C324A`) with `data-selected="true"`, larger, drawn last;
  - a `<title>` in each circle: "Team · rank R · value", with value formatted with the category's decimals (`.473` style for ratios, one decimal for counts);
  - the `<svg>` has `data-testid="league-shape"`, `role="img"` and `aria-label="League shape: <category>"`; a caption "League shape";
  - use the theme's CSS variables where they fit, adding `--gap`, `--climb` and `--cushion` next to them.

  Draw only what the API sends: no sorting or ranking in TypeScript (FR-011).
- [X] T010 [US1] In `frontend/src/components/CategoryCurves.tsx`, render `LeagueShapeChart` under each category's `CurveChart` when `result.league_shape` is non-null, matched by `category`, at the same measured width. Keep the existing curve unchanged.

**Checkpoint**: the strategic breakdown shows League shape per category; tactical is unchanged.

---

## Phase 4: User Story 2 - See which ranks are unusually cheap or expensive (P1)

**Goal**: each strategic category shows Against null with the climb and cushion marked (FR-004, FR-005, FR-007, FR-008, FR-012, FR-013).

**Independent Test**: each category with ≥ 3 teams has N − 1 bars and a null line; the climb bar and cushion bar are marked when they exist.

- [X] T011 [P] [US2] Extend `frontend/tests/league-shape.test.tsx`:
  - each category block has an Against null chart (`data-testid="against-null"`) with `gaps.length` bars and a null line;
  - bars carry `data-mark` = `climb` / `cushion` matching the API, with at most one of each;
  - a category whose `gaps` is empty renders no Against null chart (patch a fixture copy);
  - the breakdown help includes the new reading lines in strategic mode only and stays ≤ 120 words (the existing `frontend/tests/help-content.test.ts` checks the limit).
- [X] T012 [US2] In `frontend/src/components/LeagueShape.tsx`, add `AgainstNullChart({ shape, decimals, width })`:
  hand-drawn SVG as in T009:
  - one `<rect>` per gap at x = `to_place` in `--gap` (`#F5C1A9`), with `data-mark="climb"` in `--climb` (`#1C324A`) and `data-mark="cushion"` in `--cushion` (`#9DC0F5`) when marked;
  - a dotted `<polyline>` of `null_gap` in `--avg` (`#898240`, dasharray "2,3") with `data-testid="null-line"`;
  - a `<title>` in each bar: "to place r · gap · normal gap", formatted as in T009;
  - the `<svg>` has `data-testid="against-null"`; a caption "Against null". Render nothing when `gaps` is empty (FR-012).

  Render it under League shape in `frontend/src/components/CategoryCurves.tsx`.
- [X] T013 [US2] In `frontend/src/help/content.ts`, add the contracts/ui.md reading lines to the `breakdown` topic for strategic mode only. Use plain words and no file names; keep the topic ≤ 120 words, tightening existing lines if needed.

**Checkpoint**: both charts per category, marks correct, help updated.

---

## Phase 5: User Story 3 - See how moves change the shape (P2)

**Goal**: charts follow moves, and League shape shows the selected team's pre-move position (FR-009, FR-010, SC-004).

**Independent Test**: after a move that changes the team's place in a category, the selected dot is at the new place and a before marker is at the old one; without moves there's no before marker.

- [X] T014 [US3] In `backend/src/ffmodel/tools/impact_analysis/analysis.py`, fill `before` in `_league_shape` from `reuse` (the original Computed): run `league_shape(reuse.averages, fmt)` and take the selected team's `{place, rank, value}` per category (research R5). It's null when `reuse` is None or the original value is missing. Then re-copy `league_shape` from a fresh export into `frontend/tests/fixtures/strategic*.json`, as in T007, so `strategic_moves.json` carries `before`.
- [X] T015 [P] [US3] Extend `backend/tests/integration/test_impact_shape.py`:
  - without moves, every `before` is null;
  - with a move that changes the selected team's values (e.g. `Swap(acquire_id=fx.ALPHA_1, give_id=fx.DELTA_1)` for Deltas), every category's `before` equals the no-move analysis's selected place, rank and value, and the selected team's current place equals the moved analysis's rank order;
  - values reflect the moved rosters (they differ from the no-move values for the selected team).
- [X] T016 [US3] In `frontend/src/components/LeagueShape.tsx`, draw `before` as a hollow `#aaa` `<circle data-testid="shape-before">` with a `<title>` with the title "before your moves · rank R · value". Add a test in `frontend/tests/league-shape.test.tsx` using `frontend/tests/fixtures/strategic_moves.json`: the before marker renders with moves and not without. Add the help clause about the before marker (contracts/ui.md) if it isn't already in T013's line.

**Checkpoint**: moves update both charts, with the before marker.

---

## Phase 6: Polish & cross-cutting

- [X] T017 [P] In `docs/style.md`, under "Distributions and Radar", add a "League shape" subsection documenting the two idioms and their colors (research R7). This is Constitution V: a new visual idiom needs the style guide amended.
  - **Rank ladder**: muted secondary points and line; the selected team in primary `#1C324A`; the before marker hollow `#aaa`.
  - **Gap bars against a null line**: light-secondary bars; climb `#1C324A`, cushion `#9DC0F5`; null line dotted tertiary `#898240`.
- [X] T018 [P] Update `docs/tool1-impact-analysis.md`, in the Simulation Visualizer section, with the two charts in plain words: the league shape, the gaps against a normal league, climb and cushion, and that they're strategic only.
- [X] T019 Run quickstart §2 on the real league: time a cold strategic analysis (best of 3) on this branch and on the 007 tip, checked out in a temporary `git worktree` so the user's uncommitted files are never touched. PASS if this branch is ≤ 5% slower (SC-005).
- [X] T020 Run the full gates: `uv run pytest -q`, `uv run ruff check src tests`, `uv run ruff format --check src tests` and `uv run lint-imports` in `backend/`; `npm test` and `npm run build` in `frontend/`. All pass, including 007's test that Last 15 reproduces the pre-feature results (SC-006). Check the charts by eye at the narrowest breakdown grid width (FR-014).

---

## Dependencies & execution order

- **Setup (T001)** → **Foundational (T002–T007)** → stories.
- **US1 (T008–T010)** depends on Foundational. It's the MVP.
- **US2 (T011–T013)** depends on Foundational and on T010 (it renders in the same block). Its frontend code shares `LeagueShape.tsx` with US1, so do it after US1.
- **US3 (T014–T016)** depends on US1 (T009, the chart that shows the marker) and on T005 (the backend builder). T016's frontend test needs T014's fixture refresh.
- **Polish (T017–T020)**: T017 and T018 any time after US2; T019 and T020 last.

## Parallel opportunities

- T002 (unit tests) alongside T004 (schemas); T006 (integration tests) alongside T005 once T003 exists.
- T008 alongside T009; T011 alongside T012.
- T015 alongside T014.
- T017 and T018 together.

### Example: Foundational in parallel

```text
T002 core unit tests        T004 API models
T003 core/sim/shape.py      → T005 tool wiring + T006 integration tests
T007 regenerate types and fixtures
```

## Implementation strategy

1. **MVP**: Setup → Foundational → US1. League shape per category with your dot marked.
2. **US2**: Against null with the climb and cushion, plus help.
3. **US3**: the before marker after moves.
4. **Polish**: style guide, docs, timing, gates.
