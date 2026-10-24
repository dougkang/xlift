---

description: "Task list for Move Impact Highlighting"
---

# Tasks: Move Impact Highlighting

**Input**: Design documents from `specs/003-move-impact-diff/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (api.md, ui.md), quickstart.md

**Tests**: Included. The constitution's quality gates apply, and SC-002 to SC-005 need explicit
checks. Write each story's tests first.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 (headline), US2 (per-category and per-opponent places), US3 (settings
  consistency)

## Conventions

- **Directories:** backend code is in `backend/src/ffmodel/` and its tests in `backend/tests/`;
  frontend code is in `frontend/src/` and its tests in `frontend/tests/`.
- **Changes come from the server:** every change and tone is computed by the server (FR-017).
  The frontend only renders `result.changes`.
- **A Change:** `{delta, tone}`, or `null`. It is `null` when the delta rounds to 0 at display
  precision, or when either side is missing (research R2).
- **Tones:** decided by `tone(delta, better_when)` with `better_when ∈ {"higher", "lower",
  "neutral"}` (research R3).

---

## Phase 1: Setup

- [X] T001 Add these tokens to `frontend/src/styles/tokens.css`:
  - `--better: #5c8e4e`
  - `--worse: #c00`
  - `--before-line: #aaa`
  - `--before-fill: #eee`
- [X] T002 [P] Add a "Change (before/after)" section to `docs/style.md`, per research R6. Also widen
  the "Red `#c00`" rule from two permitted uses to three: destructive hover, status, and a change
  for the worse (FR-018).

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T003 Create `backend/src/ffmodel/tools/impact_analysis/changes.py` with:
  - **`tone(delta, better_when) -> str`**: `"better"` / `"worse"` / `"neutral"`. `better_when` is
    `"higher"`, `"lower"` or `"neutral"`.
  - **`change(current, original, *, decimals, better_when, scale=1.0) -> dict | None`**:
    - computes `round((current − original) * scale, decimals)`;
    - returns None if either value is None or non-finite, or if the rounded delta is 0;
    - otherwise returns `{"delta": d, "tone": tone(d, better_when)}`.
  - **Precision constants** from research R2:
    - counts and ranks: 0 decimals;
    - percentages: 0 decimals with `scale=100`;
    - area score: 0 decimals with `scale=100`;
    - counting averages: 1 decimal;
    - ratio averages: 3 decimals.

    Add a helper `avg_decimals(category) = 3 if kind == "ratio" else 1`.
  - **`transition(original, current) -> str | None`**: order L < T < W. L→W is `flip_better`,
    W→L is `flip_worse`; any other increase is `better`, any other decrease `worse`; equal is
    None.
- [X] T004 [P] Write `backend/tests/unit/test_changes.py` covering:
  - **Tone table:** every `better_when`, including the inverted cases:
    - L uses `lower`;
    - rank uses `lower`;
    - a lower-is-better category average uses `lower`;
    - Opp average uses the opposite of the category direction;
    - T, League average and Leader average are `neutral`.
  - **Rounding to zero gives None:** at each precision, e.g. 0.04 at 1 decimal, 0.0004 at
    3 decimals, 0.004 as a percentage.
  - **None and NaN inputs** give None.
  - **All 9 transition pairs.**
- [X] T005 Refactor `backend/src/ffmodel/tools/impact_analysis/analysis.py` into two steps.
  1. **`_compute(conn, s, state, fmt, projections, reuse=None) -> Computed`**:
     - `Computed` holds `samples`, `values`, `averages`, `ranks`, `normalized`, `win_rates`,
       `area_scores`, `odds` per opponent (all teams vs selected, under the mode's k), and
       `active` per team (a frozenset).
     - With `reuse=Computed`: copy `samples[tid]` from `reuse` for every team whose `active`
       frozenset is equal, and simulate only the rest (research R1).
  2. **`_render(s, state, fmt, projections, comp) -> dict`**: the existing result-building code,
     moved unchanged.

  `analyze()` behaves exactly as before when there are no moves: every 002 test must still pass
  unchanged.
- [X] T006 Add an original-analysis cache to `backend/src/ffmodel/tools/impact_analysis/cache.py`:
  - `original_cache`: an LRU with **maxsize 8**;
  - the key: "(db url, league, team, mode, window, as_of, period, opponent, seed, iterations,
    latest `load_run` ID)";
  - the value: `(state, projections, Computed)` for the no-moves scenario;
  - `clear()` clears both caches.
- [X] T007 Add to `backend/src/ffmodel/api/schemas.py`:
  - `Change {delta: float, tone: Literal["better","worse","neutral"]}`;
  - `MatchupChange`, `HeaderChange`, `RadarChange`, and `Changes`, per
    data-model.md and contracts/api.md;
  - `AnalysisResult.changes: Changes | None = None`;
  - `selected_original` added to `CurveRole`.

  Every Change-valued field is `Change | None`.
- [X] T008 Implement `build_changes(original, current, s, fmt, state, original_state, names) ->
  dict` in `changes.py`. Original and current are `Computed` plus the rendered dicts. It builds
  every part of the `changes` block per contracts/api.md:
  - `header`
  - `radar` (`original` series for the selected team, plus the opponent if its `active`
    changed; `tones` per scale; `area`)
  - `category_table`
  - `curves.means`
  - `matchups`, keyed by opponent ID string
  - `matchup_totals`

  Use `tone` and `change` only; never compare in place.
- [X] T009 Wire `analyze()`:
  - **No moves** (or `OPPONENT_REQUIRED`): `changes = None`.
  - **With moves:**
    1. get or compute the original from `original_cache`;
    2. compute the current with `reuse=original`;
    3. render the current;
    4. recompute curves with the selected team's original series added (`selected_original`
       only) through one `density_curves` call per category, so all series share a grid
       (research R5);
    5. set `result["changes"] = build_changes(...)`.
- [X] T010 [P] Create `frontend/src/components/Delta.tsx`:
  - **`<Delta change={Change|null} decimals={number} ratio?={boolean} />`**: renders nothing when
    `change` is null. Otherwise it renders a small `<span className="delta delta-<tone>">`:
    - `+` or `−` (U+2212);
    - `|delta|` with `decimals` decimals, and the leading zero stripped when `ratio`;
    - `aria-label="up 2, better"`.
  - **Styles** in `frontend/src/styles/base.css`:
    - `.delta { font-size: var(--header-size); margin-left: .15rem; font-weight: 400 }`
    - `.delta-better { color: var(--better) }`
    - `.delta-worse { color: var(--worse) }`
    - `.delta-neutral { color: var(--muted) }`
  - **No wrapping (FR-019):** export `<WithDelta>` (value + Delta inside
    `<span className="nowrap">`). Every place uses it, so a value and its delta never wrap apart.
    Delta text has no parentheses in tables and adds no padding beyond the `.15rem` gap.
- [X] T011 Add an export of `frontend/tests/fixtures/strategic_moves.json` and
  `frontend/tests/fixtures/tactical_moves.json` to
  `backend/tests/fixtures/export_frontend_fixtures.py`. Use the impact fixture:
  - **strategic:** Gammas with moves `[Drop(GAMMA_2), Add(BUSY)]`;
  - **tactical:** Gammas vs Betas with a trade, `Swap(acquire=BETA_1, give=GAMMA_2)`.

  Regenerate the API types with `npm run gen:api`.

**Checkpoint**: unit tests pass, and the 002 suite is unchanged and green. A request with moves
returns a full `changes` block.

---

## Phase 3: User Story 1 - See the net effect of my moves at a glance (Priority: P1) 🎯 MVP

**Goal**: show the headline changes. In strategic mode, the W/L/T record. In tactical mode, the
chance to win.

**Independent Test**: a move changes the Aggregated Record, and the W/L/T deltas appear with the
right colors. Reset removes every marker.

- [X] T012 [P] [US1] Write `backend/tests/integration/test_impact_changes.py::test_headline` (on
  `impact_engine`):
  - **No moves:** `changes is None`.
  - **Strategic with moves:** `header` W/L/T Changes equal the current minus the original
    record, with W tone `better` when positive and L tone `better` when negative.
  - **Tactical:** `chance_to_win` equals the round of (current − original win) × 100.
- [X] T013 [P] [US1] Write `frontend/tests/changes.test.tsx::headline`:
  - **Strategic:** with `strategic_moves.json`, each W/L/T digit has a `Delta` with the fixture's
    tone class.
  - **Tactical:** with `tactical_moves.json`, Chance to Win has a `Delta`.
  - **No changes:** with `strategic.json` (`changes: null`), no `.delta` elements exist.
- [X] T014 [US1] Update `frontend/src/components/RecordHeadline.tsx` (deltas raised inline, never
  a new line; the record keeps one line and its height, per FR-019):
  - **Strategic:** render W, L and T as separate spans, each followed by
    `<Delta change={changes.header.wins|losses|ties} decimals={0} />`.
  - **Tactical:** render `<Delta change={changes.header.chance_to_win} decimals={0} />` after the
    percentage.

**Checkpoint**: the headline tells whether a move helped, without remembering anything.

---

## Phase 4: User Story 2 - See which categories and opponents changed (Priority: P1)

**Goal**: inventory rows 3 to 9: radar, tabs, the two tables, curves, H2H rows, and H2H total.

**Independent Test**: a move that helps REB and hurts AST shows green and red on the radar, in the
table, and in the curves. H2H flips are bold.

### Tests

- [X] T015 [P] [US2] Add to `backend/tests/integration/test_impact_changes.py`:
  1. **Free-agent add touches only Gammas:** for every other team, the reused samples are the
     same objects or equal arrays. Their `matchups` entries differ only through Gammas. The
     `league_average` and `leader_average` Changes are null in categories where the league
     values didn't move (SC-003).
  2. **Category table:** per category, `rank` and `average` deltas equal the current minus the
     original (rounded). The TO average delta has the inverted tone.
  3. **Radar:** `original` has 1 series (strategic). `tones` has 3 scales × 9 categories. Each
     non-null tone matches the sign of (current − original) for that scale (rank inverted).
     The `area` Changes are present.
  4. **Curves:** every curve has `selected_original` on the same `x` grid. `means.selected`
     matches the current average minus the original average.
  5. **Transitions:** each opponent's `transition` equals `transition(original_result, result)`.
     `original_result` matches the original analysis.
  6. **Tactical trade with Betas:**
     - `radar.original` includes Betas;
     - curves include `selected_original` and no `opponent_original` (revised);
     - the `category_table` has `opponent_average` Changes with inverted tones.
  7. **The original cache is hit:** a second request with different moves doesn't call the
     original compute again. Patch a counter to check.
- [X] T016 [P] [US2] Add to `frontend/tests/changes.test.tsx`, covering the places in the spec's
  inventory:
  - **Radar:** a dashed original outline (`data-testid="radar-original"`), plus colored segments
    (`data-testid="radar-change-<tone>"`) in the counts implied by the fixture's tones for the
    active scale.
  - **Tabs:** each tab has a `Delta`.
  - **Ranking table:** Deltas in the Rank, Avg and Win % cells.
  - **Tactical difference table:** Deltas in You, Opp, Diff and Win %.
  - **Curves:** each chart renders an original series, and the average labels include
    "(+…)" / "(−…)".
  - **H2H:** the Result cell has the `flip-better` / `flip-worse` classes for flips, and the
    Deltas on the H2H counts and Win % and in the total row are present.
  - **Roster:** unchanged. No rows are added for dropped players (FR-014, option A).

### Implementation

- [X] T017 [P] [US2] Update `frontend/src/components/Radar.tsx`. Add a `changes` prop. Under the
  active scale:
  - **Original outline:** draw `changes.radar.original` series as dashed `--before-line`
    outlines with no fill, after the selected fill.
  - **Spoke segments:** for each category with a non-null tone, draw a 3px line along the spoke
    from the original radius to the current radius, with a dot at the current radius, in the
    tone color.
  - **Test IDs:** `radar-original` and `radar-change-<tone>`.
- [X] T018 [P] [US2] Update the radar tabs in `frontend/src/App.tsx`. Append
  `<Delta change={changes.radar.area[scale]} decimals={0} />` after each tab's score.
- [X] T019 [P] [US2] Update `frontend/src/components/CategoryTable.tsx`. Append a Delta after
  every value cell, using `changes.category_table[cat][field]`.
  - **Decimals:** 0 for rank, `avg_decimals` for averages (3 for ratios, with `ratio`), and 0 for
    percentages.
- [X] T020 [P] [US2] Update `frontend/src/components/CategoryCurves.tsx` (label text
  `You 412.3 +18.0`, no parentheses):
  - **Draw order:** draw `selected_original` first, as `--before-fill`
    areas with `--before-line` outlines.
  - **Exclusions:** leave them out of the legend and the mean-line labels.
  - **Label deltas:** add `(+x)` / `(−x)`, in the tone color, to the "You" and "Opp" average
    labels from `changes.curves[cat].means[role]`. Extend `placeLabels` to use the longer text.
- [X] T021 [P] [US2] Update `frontend/src/components/RecordTable.tsx`:
  - **Deltas** on the H2H W/L/T, Win % (points) and Total cells.
  - **Result cell classes:**
    - `flip_better` → `flip-better` (bold `--better`);
    - `flip_worse` → `flip-worse` (bold `--worse`);
    - `better` / `worse` → `result-better` / `result-worse` (colored, not bold).
  - **Title:** "was W/L/T".
  - Add the styles to `base.css`.
- [X] T022 [P] [US2] Leave `frontend/src/components/Roster.tsx` unchanged: no rows for dropped or
  traded-away players (FR-014, option A). Confirm that no `removed_players` field or render path
  exists.
- [X] T023 [US2] Update `frontend/src/format.ts` so counting-category averages always show
  1 decimal (research R2), and update any test expectations it affects.

**Checkpoint**: all 9 inventory places show changes (SC-004).

---

## Phase 5: User Story 3 - Compare consistently across settings (Priority: P2)

**Goal**: changing the settings, the team or the scale keeps the comparison fair.

**Independent Test**: after a move, change the window from 15 to 10. The deltas still describe
only the move.

- [X] T024 [P] [US3] Add to `backend/tests/integration/test_impact_changes.py`:
  - **Window:** with moves, a window of 10 gives deltas equal to analyze(window=10, moves) minus
    analyze(window=10, no moves). The original is never reused across windows.
  - **Selected team:** switching the selected team compares that team's original roster
    against its current one.
  - **Opponent:** switching the tactical opponent recomputes the original for the new opponent.
- [X] T025 [P] [US3] Add a test to `frontend/tests/changes.test.tsx`: switching the radar scale
  re-renders the original outline and spoke segments from that scale's tones. Check the
  `radar-change-*` counts for each scale.

(These requirements come for free from the cache key and the per-scale tones built in Phase 2.
This phase only verifies them.)

---

## Phase 6: Polish & Cross-Cutting

- [X] T025a [P] Add a layout-stability test, `frontend/tests/layout.test.tsx` (FR-019, SC-007):
  render with `strategic_moves.json` and `tactical_moves.json` and check that:
  - every element containing a `.delta` is inside a `.nowrap` ancestor, or is a cell with
    `white-space: nowrap`;
  - no `<br>` or block element is inserted by a Delta.

  Also add `.nowrap` to every delta-bearing table cell (`td` with a Delta) in
  `frontend/src/styles/base.css`.
- [X] T026 Add to `backend/tests/slow/test_real_league.py` a case `test_sc001_with_moves`:
  - **Moves:** drop the selected team's first active player and add the first free agent.
  - **Timing:** both the cold call (original not cached) and the warm call (original cached)
    take under 2.0 s, in both modes. Print the timings.
- [X] T027 [P] Update the 002 and 003 contracts and docs:
  - **`specs/002-impact-analysis/contracts/ui.md`:** add a note pointing to 003 for change
    markers;
  - **`backend/README.md`:** a line on `changes`.
- [X] T028 Run the checks:
  - `uv run ruff check src tests`, `uv run lint-imports`, `uv run pytest`, and
    `uv run pytest -m slow`;
  - `npm test` and `npm run build`.

  Fix any findings.
- [X] T029 Run quickstart sections B and C. For SC-007, compare the page at 1,100 px and 900 px
  with and without moves: no line breaks, and no section moves. Append a "Validation log" to
  `specs/003-move-impact-diff/quickstart.md`.

---

## Dependencies & Execution Order

- **Setup:** T001 and T002 can run in parallel.
- **Foundational:**
  - T003 → T004 can run in parallel with T005;
  - T005 → T006 → T008 → T009;
  - T007 is needed by T009;
  - T010 can run in parallel;
  - T011 needs T009.
- **US1** (T012–T014) and **US2** (T015–T023) need Phase 2. Their frontend components are
  different files, so they can be built in parallel.
- **US3** needs Phase 2. It only verifies behavior and can run in parallel with US2.
- **Polish** needs everything.
- **Shared files:**
  - `App.tsx`: only T018 edits it;
  - `base.css`: T010, then T021 (in that order);
  - `test_impact_changes.py`: T012, then T015, then T024 (in that order);
  - `changes.test.tsx`: T013, then T016, then T025 (in that order).

## Parallel Examples

```bash
# After T009 and T011:
Task: "T014 RecordHeadline"   Task: "T017 Radar"   Task: "T019 CategoryTable"
Task: "T020 CategoryCurves"   Task: "T021 RecordTable"   Task: "T022 Roster"
```

## Implementation Strategy

1. **MVP** (Phases 1–3): the backend's full `changes` block plus the headline deltas. This
   already answers "did this move help?".
2. **US2:** every other place, the full inventory.
3. **US3 checks**, then **Polish**: the timing on the real league and the validation log.
