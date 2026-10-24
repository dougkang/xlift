---
description: "Task list for 005 Current Matchup (Tactical Week-to-Date Actuals)"
---

# Tasks: Current Matchup (Tactical Week-to-Date Actuals)

**Input**: Design documents from `specs/005-tactical-actuals/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (matchups-csv, api, ui),
quickstart.md

**Tests**: Included. The spec's success criteria (SC-001 – SC-005) and quickstart §B call for
automated checks.

**Story order**:
- **US2 (import) before US1:** both are P1, but US1 needs a matchup state to exist, so US2 is
  implemented first.
- **US3 (P2) last.**

**Fixture conventions** (`backend/tests/fixtures/impact_dataset.py`): `IMPACT_TODAY` = 2026-11-18,
`WEEK` = 2026-11-16 – 2026-11-22, `LAST_FINAL` = 2026-11-17.

## Phase 1: Setup

- [X] T001 Confirm the baseline is green before changes: `cd backend && uv run pytest -q && uv run ruff check . && uv run lint-imports`, then `cd frontend && npm test`.

## Phase 2: Foundational (blocks all stories)

- [X] T002 Create migration `backend/src/ffmodel/contract/migrations/0002_matchup_state.sql` exactly as in data-model.md:
  - **`matchup_state`:** one row per league, `league_id` PRIMARY KEY. Columns `week` (`CHECK (week >= 0)`), `period_start`, `period_end` (`CHECK (period_end >= period_start)`), `as_of`, and `run_id` (a reference to `load_run`).
  - **`matchup_team`:** PRIMARY KEY `(league_id, fantasy_team_id)` with `opponent_team_id`, plus these checks:
    - `fga >= fgm`, `fg3m >= 0 AND fg3m <= fgm`, `fta >= ftm`;
    - `reb`, `ast`, `stl`, `blk` and `tov` all `>= 0`;
    - `pts = 2 * fgm + fg3m + ftm`;
    - `opponent_team_id <> fantasy_team_id`.

  Verify that `uv run ffm db migrate` applies it and `ffm db version` reports 2.
- [X] T003 [P] Add `MatchupLine(team_id, opponent_id, totals: dict[str, int])` and `MatchupState(league_id, week, period_start: date, period_end: date, as_of: date, loaded_at: str, lines: dict[int, MatchupLine])` dataclasses in `backend/src/ffmodel/core/data/models.py`. Add `matchup_as_of: str | None` to `DataFreshness`.
- [X] T004 Implement `get_matchup_state(conn, league_id) -> MatchupState | None` in a new `backend/src/ffmodel/core/data/matchup.py`. It joins `matchup_state`, `matchup_team` and `load_run.finished_at` (as `loaded_at`). Export it from `backend/src/ffmodel/core/data/__init__.py`, and fill `matchup_as_of` in `get_data_freshness` in `backend/src/ffmodel/core/data/bulk.py`.
- [X] T005 [P] Add a `file_date(path) -> date` helper (the file's mtime, in local time) to `backend/src/ffmodel/adapters/common.py`.
- [X] T006 Extend `backend/tests/fixtures/impact_dataset.py` with `load_matchup_state(conn, as_of=LAST_FINAL)`. It writes:
  - a `load_run` row;
  - `matchup_state` for week 1, period `WEEK`;
  - `matchup_team` lines for the fixture's 4 teams, paired Alphas–Betas and Gammas–Deltas, with hand-chosen consistent totals where `pts` equals `2*fgm + fg3m + ftm`.

  Expose the constants `MATCHUP_TOTALS` and `MATCHUP_PAIRS`. Don't call it from `load_impact_fixture`, so strategic tests stay unaffected.

**Checkpoint**: the schema and the read model exist; no behavior has changed yet.

## Phase 3: User Story 2 — Import the current matchup state (P1)

**Goal**: `ffm load matchups` loads the exporter's `matchups.csv` all-or-nothing. As-of and
period are inferred from the file's modified date. The roster import also uses its file's
modified date.

**Independent test**:
1. Import `~/dev/ccsv-rumble-page/data/matchups.csv`. The summary shows week 1, the period, the
   as-of date and 9 pairings.
2. Re-import replaces the state.
3. A tampered file is rejected and nothing is written.

### Tests for User Story 2

- [X] T007 [P] [US2] Write unit tests in `backend/tests/unit/test_matchup_parse.py` for `parse_matchups_csv`:
  - **Valid file:** a valid file parses; `tpm` maps to `fg3m` and `to` to `tov`; extra columns are ignored.
  - **Rejections:** each label in contracts/matchups-csv.md is produced: `MISSING`, `MALFORMED`, `DUPLICATE`, `BAD_PAIRING` (self and non-mutual), `INCONSISTENT` (week differs), and `BAD_TOTALS` (fgm>fga, ftm>fta, tpm>fgm, pts mismatch).
- [X] T008 [P] [US2] Write integration tests in `backend/tests/integration/test_matchup_load.py` (DB):
  - load succeeds into the impact fixture league using `team_id` = `source_team_key`;
  - `UNKNOWN_TEAM` and `MISSING_TEAM` are rejected with nothing written;
  - re-import replaces the rows, leaving one `matchup_state` row;
  - `--as-of` defaults to the file's mtime (set it with `os.utime`) and the period to that week's Monday–Sunday;
  - explicit `as_of` and period override the defaults;
  - a `load_run` is recorded with source `matchups_csv`.

  Add a `live`-marked test that loads `~/dev/ccsv-rumble-page/data/matchups.csv` into a league built from `rosters.csv`, and asserts 18 teams, 9 pairs, and under 5 seconds (SC-004).
- [X] T009 [P] [US2] Add a test to `backend/tests/integration/test_roster_loader.py`: with no `as_of`, `player_status.as_of` equals the roster file's mtime date.

### Implementation for User Story 2

- [X] T010 [P] [US2] Implement `backend/src/ffmodel/adapters/matchup_csv/parse.py`:
  - **Output:** `MatchupRow` (line_no, week, team_key, opponent_key, fgm, fga, fg3m, ftm, fta, reb, ast, stl, blk, tov, pts) and `Problem(kind, message, line_no)`.
  - **Required columns:** `week, team_id, opponent_id, fgm, fga, ftm, fta, tpm, pts, reb, ast, stl, blk, to`. Ignore other columns.
  - **File-level checks:** labels as in contracts/matchups-csv.md. Use `utf-8-sig` like `roster_csv/parse.py`.
- [X] T011 [US2] Implement `backend/src/ffmodel/adapters/matchup_csv/loader.py` with `load_matchups(engine, path, league_key, *, as_of=None, period_start=None, period_end=None) -> LoadSummary`:
  - **Defaults:** `as_of = as_of or file_date(path)`; the period defaults to the Monday–Sunday week containing `as_of`.
  - **Validation:** resolve team keys against `fantasy_team.source_team_key` for the league. Report `UNKNOWN_TEAM` and `MISSING_TEAM`.
  - **Writing:** in one transaction, delete the league's `matchup_team` and `matchup_state` rows and insert the new ones.
  - **Run record:** record the run with `start_run` and `finish_run` (source `matchups_csv`, scope `league:<key>`). On problems, mark it `rejected` with a report like the roster loader's `format_report`.
  - **Summary extras:** week, period, as_of and pairings (team names).
  - Add `backend/src/ffmodel/adapters/matchup_csv/__init__.py`.
- [X] T012 [US2] Change the default `as_of` in `load_roster` in `backend/src/ffmodel/adapters/roster_csv/loader.py` from `date.today()` to `file_date(path)`.
- [X] T013 [US2] Add `@load_app.command("matchups")` to `backend/src/ffmodel/cli.py`:
  - **Arguments:** `PATH`, `--league-key`, `--as-of`, `--period-start`, `--period-end`, plus `--json` through `_emit`.
  - **Output:** print the week, period, as-of and pairings.
  - **Exit codes:** 0 on success, 2 when rejected, 1 on errors.

  Update the `load roster` `--as-of` help to say "defaults to the file's modified date".
- [X] T014 [US2] Run `uv run ruff check . && uv run lint-imports` from `backend/`. The `adapters-independent` contract must hold: no `ffmodel.core` imports from `adapters/matchup_csv`.

**Checkpoint**: matchup state can be imported and inspected; analysis doesn't use it yet.

## Phase 4: User Story 1 — See who wins my current matchup (P1) 🎯 MVP

**Goal**: tactical is the selected team's current matchup. Totals are the week-to-date base plus
simulated games after the as-of date. There are no opponent or period inputs.

**Independent test**:
- **Opponent:** with the fixture's matchup state, tactical for Gammas shows Deltas.
- **Means:** each category's mean equals base + mean of remaining.
- **Final week:** with as_of = period end, odds are 0, ½ or 1 and match the base comparison.
- **Strategic:** results are unchanged.

### Tests for User Story 1

- [X] T015 [P] [US1] Write unit tests in `backend/tests/unit/test_engine_base.py` for `simulate_team(base=...)`:
  - **No base:** `base=None` gives identical samples to today (same seed).
  - **With base:** every sample equals the base plus the base-less sample, after the remainder is clipped and rounded.
  - **Constraints:** `fgm <= fga` still holds.
  - **No remaining games:** all players have `games_remaining=0`, so samples equal the base exactly.
  - **Derived points:** `pts` is derived from the summed totals.
- [X] T016 [US1] Rewrite `backend/tests/integration/test_impact_tactical.py` around the matchup state, loading it with `load_matchup_state(conn)`:
  - **Opponent:** comes from the pairing for every fixture team (SC-001).
  - **Request inputs:** `opponent_id` and period are no longer inputs.
  - **Means:** per-category mean final total ≈ base + mean of a base-less run (SC-002; ratios from combined makes and attempts).
  - **Remaining window:** per player, games after the as-of date through the period end, counted by date even when a game after the as-of date is still `scheduled` in a state that was final at capture.
  - **Final week:** with `as_of` = period end, odds are 0, ½ or 1, `header.matchup.final` is true, and the result matches `current` (SC-003).
  - **Moves:** dropping a player changes the averages but not `current` or the `*_actual` values (FR-010).
  - **Warnings:**
    - no state gives `MATCHUP_NOT_LOADED` and no tactical results;
    - a `final` game after the as-of date gives `MATCHUP_STALE`;
    - roster as-of ≠ matchup as-of gives `ROSTER_MATCHUP_DATES_DIFFER`.
- [X] T017 [P] [US1] Add a strategic regression test to `backend/tests/integration/test_impact_strategic.py`: the strategic result JSON is identical with and without `load_matchup_state` (SC-005).
- [X] T018 [P] [US1] Update `backend/tests/integration/test_impact_changes.py` for tactical: before and after share the same base (FR-019). Remove `opponent_id` and period arguments.

### Implementation for User Story 1

- [X] T019 [US1] Add `base: np.ndarray | None = None` to `simulate_team` in `backend/src/ffmodel/core/sim/engine.py`. With a base, the steps are:
  1. clip and round the remainder;
  2. apply `subset_constraints` to the remainder;
  3. add `base` per base stat;
  4. compute `derived_stats`.

  Without a base, the code path is unchanged.
- [X] T020 [P] [US1] Add core helpers in `backend/src/ffmodel/core/data/matchup.py`, or a new `backend/src/ffmodel/core/sim/matchup.py` if keeping core.data scoring-free is preferred:
  - `base_vector(line, fmt) -> np.ndarray` in `fmt.base_stats` order; it raises `MissingStats(names)` when a base stat isn't in `line.totals`;
  - `actual_values(line, fmt) -> np.ndarray`, the category values of the base, with ratios null when attempts are 0;
  - `current_record(a, b, fmt) -> (wins, losses, ties)` via `fmt.compare`.
- [X] T021 [US1] In `backend/src/ffmodel/core/model/projection.py`, make `period` mean the remaining-games window `(start, end)`, used as-is with no `max(as_of, …)`. In `backend/src/ffmodel/core/data/bulk.py` `count_team_games_bulk`, add a `statuses` option so callers can exclude `postponed` and `cancelled` games. Tactical passes `("scheduled", "final")`, so remaining games are chosen by date (research R2, R4).
- [X] T022 [US1] Update `backend/src/ffmodel/tools/impact_analysis/settings.py`:
  - remove `opponent_id`, `period_start` and `period_end` as user inputs, and add derived fields `matchup_as_of`;
  - for tactical, `normalize(s, state)` fills the opponent from `state.lines[team_id].opponent_id`, the period from the state, and the remaining window `(as_of + 1 day, period_end)`, which is empty when `as_of >= period_end`.
- [X] T023 [US1] Update `backend/src/ffmodel/tools/impact_analysis/cache.py`: the projection key uses the remaining window instead of the user period, and the original key drops `opponent_id` and period in favor of the derived values. The latest `run_id` already invalidates on re-import.
- [X] T024 [US1] Rework the tactical branch of `backend/src/ffmodel/tools/impact_analysis/analysis.py`:
  - **State:** load it with `get_matchup_state`; with none, add `MATCHUP_NOT_LOADED` and return like today's `OPPONENT_REQUIRED` path (remove that code).
  - **Simulation:** pass `base=base_vector(state.lines[tid], fmt)` to `simulate_team` for every team in `_compute`, tactical only, which keeps the radar ranks consistent.
  - **`header.matchup`:** opponent id and name, week, period, as_of, `final` (`as_of >= period_end`), and `current` from `current_record`.
  - **`DifferenceRow`:** add `selected_actual` and `opponent_actual` from `actual_values`.
  - **Matchups:** set `matchups=[]` and `matchup_totals=None`.
  - **Warnings:** add `MATCHUP_STALE` (any `final` game for a rostered player's NBA team with as_of < date ≤ today), `ROSTER_MATCHUP_DATES_DIFFER` (freshness `roster_as_of` ≠ state `as_of`) and `MATCHUP_STATS_MISSING`. Keep `NO_GAMES_REMAINING` as informational.
- [X] T025 [US1] Update `backend/src/ffmodel/api/schemas.py`:
  - **`ScenarioRequest`:** remove `opponent_id`, `period_start`, `period_end` and their validator.
  - **New `MatchupHeader`:** `opponent_id`, `opponent_name`, `week`, `period_start`, `period_end`, `as_of`, `final`, `current: WLT`, carried as `Header.matchup: MatchupHeader | None`.
  - **`DifferenceRow`:** add `selected_actual` and `opponent_actual: float | None`.
  - **New `CurrentMatchup`:** `week`, `period_start`, `period_end`, `as_of`, `loaded_at`, carried as `LeagueDetail.current_matchup: CurrentMatchup | None`.
  - **`Freshness`:** add `matchup_as_of`.

  In `backend/src/ffmodel/api/routes.py`, `_settings` stops passing the opponent and period, and `league_detail` fills `current_matchup` from `get_matchup_state`.
- [X] T026 [US1] Update the API tests that send `opponent_id` or period: `backend/tests/integration/test_api_*.py` and `test_impact_moves.py`. Then run `uv run pytest -q`; T015–T018 must pass.
- [X] T027 [US1] Update `backend/tests/fixtures/export_frontend_fixtures.py` to load the matchup state for the tactical fixtures. Regenerate with `uv run python -m tests.fixtures.export_frontend_fixtures`. Then, with the server restarted, run `cd frontend && npm run gen:api`.
- [X] T028 [US1] Update `frontend/src/state/scenario.ts`: remove `opponentId`, `periodStart`, `periodEnd`, `setOpponent` and `setPeriod`; loading an old saved session must ignore those keys. Update `toRequest` in `frontend/src/App.tsx` so it no longer sends opponent or period.
- [X] T029 [US1] Update `frontend/src/components/Controls.tsx`:
  - remove the vs and Week controls and the `period` prop;
  - `ModeToggle` takes `league` and disables Tactical when `league?.current_matchup` is null, with the title "Import matchups.csv to see the current matchup".

  Remove the `period` prop usage from `frontend/src/App.tsx`.
- [X] T030 [US1] Update `frontend/tests/tactical.test.tsx`, `frontend/tests/changes.test.tsx` and `frontend/tests/layout.test.tsx`:
  - **Seeding:** no `opponentId`. Tactical uses the fixture's pairing, and `league.json` includes `current_matchup`.
  - **New assertions:** no "Opponent" or "Period start" controls; Tactical is disabled when `current_matchup` is null; the opponent comes from the result.
  - Run `npm test`.

**Checkpoint**: the MVP. Tactical shows the real current matchup, with base plus remaining games.

## Phase 5: User Story 3 — Know where the matchup stands now (P2)

**Goal**: the "Now" score and as-of in the headline, week-to-date values in the difference
table, the opponent's read-only roster in place of H2H, and updated help.

**Independent test**: in tactical mode:
- the headline shows "Now W–L–T · as of <date>";
- the table shows Now values;
- the opponent's roster section has no drop buttons;
- the help tests pass within 120 words.

### Tests for User Story 3

- [X] T031 [P] [US3] Extend `frontend/tests/tactical.test.tsx`:
  - **Headline:** shows `Now W–L–T` from `header.matchup.current`, the period and the as-of date. It shows "Final" when `final` is true.
  - **Table:** the Per Category Difference table has a "Now" column with `selected_actual–opponent_actual`.
  - **Opponent roster:** a section titled with the opponent's name lists their players, with no `Drop …` buttons. There is no H2H section.
- [X] T032 [P] [US3] Update `frontend/tests/help.test.tsx` and `frontend/tests/help-content.test.ts`:
  - the topics are 10 with `opponentRoster`, and the strategic button count stays 9;
  - the settings help never mentions vs or Week, and the `vs`/`Week` assertions are removed;
  - the `mode` help mentions the current matchup and `matchups.csv`;
  - the `opponentRoster` help says read-only;
  - every topic is 120 words or fewer.

### Implementation for User Story 3

- [X] T033 [P] [US3] Update `frontend/src/components/RecordHeadline.tsx`:
  - in tactical, under the opponent line, add `<div className="matchup-line">` reading "Week N (Mon D–D) · Now W–L–T · as of Mon D", or "Final W–L–T" when `final`;
  - the W uses the existing `Wins` styling;
  - the record's baseline alignment is unchanged.
- [X] T034 [P] [US3] Update `frontend/src/components/CategoryTable.tsx` (differences kind):
  - add a muted "Now" column before You, showing `selected_actual–opponent_actual` formatted with the category's decimals ("–" when null);
  - You and Opp stay as they are (now the projected finals).
- [X] T035 [US3] Update `frontend/src/components/Roster.tsx`: take an optional `title` and a `helpTopic` prop, defaulting to "Roster" and `"roster"`. It stays read-only when `onDrop` is undefined.
- [X] T036 [US3] Update `frontend/src/App.tsx`: in tactical, render `<Roster result teamId={opponentId} title={opponentName} helpTopic="opponentRoster" />` (no `onDrop`) in `cell-h2h` in place of `RecordTable`. The opponent id comes from `result.header.matchup.opponent_id`. Strategic keeps `RecordTable`.
- [X] T037 [US3] Update `frontend/src/help/content.ts`:
  - add the `"opponentRoster"` `TopicId` and topic;
  - `settings`: remove the vs and Week controls;
  - `mode`: tactical is your current matchup from `matchups.csv`, with actual-so-far plus projected remaining games;
  - `headline` (tactical): add Now and the as-of date;
  - `categoryTable` (tactical): Now is week to date, and You and Opp are projected finals;
  - add `asOf` and `week` to `HelpContext` and fill them in `App.tsx`;
  - keep every topic at 120 words or fewer.
- [X] T038 [P] [US3] Add `.matchup-line` (muted, `--data-size`) and the Now column style to `frontend/src/styles/base.css`.
- [X] T039 [US3] Run `cd frontend && npm test && npm run build`; T031 and T032 must pass.

## Phase 6: Polish & Cross-Cutting

- [X] T040 [P] Update `docs/style.md`: document the "Now" line and column (muted, week to date), and the opponent's read-only roster replacing H2H in tactical mode.
- [X] T041 [P] Update `specs/004-section-help` help inventory notes (settings without vs and Week, new opponent-roster topic) in `specs/004-section-help/contracts/ui.md`.
- [X] T042 Run the quickstart §A import against the real files:
  1. `uv run ffm load roster ~/dev/ccsv-rumble-page/data/rosters.csv --league-key ccsv-2026`;
  2. `uv run ffm load matchups ~/dev/ccsv-rumble-page/data/matchups.csv --league-key ccsv-2026`.

  Check the printed as-of dates, the period and the 9 pairings.
- [X] T043 Run the full gates: `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run lint-imports`, then `cd frontend && npm test && npm run build`. Restart `ffm serve`.
- [X] T044 Run the browser checks in quickstart §C:
  - your real opponent is shown;
  - Now equals the file's `cat_wins` score;
  - the difference table's Now values match the file;
  - the opponent's roster is read-only;
  - a drop changes only the projections.

## Dependencies & Execution Order

- **Overall:** Setup (T001) → Foundational (T002–T006) → US2 (T007–T014) → US1 (T015–T030) → US3 (T031–T039) → Polish (T040–T044).
- **US2 dependencies:** needs T002 and T005. T010 comes before T011, and T011 before T013. T012 is independent of T010 and T011.
- **US1 dependencies:**
  - needs T003, T004 and T006, and US2 only for the real-file run (T042);
  - T019 and T020 come before T024; T021 and T022 before T023 and T024; T025 after T024;
  - T027 needs the T025 API, and T028–T030 need T027's fixtures and types.
- **US3 dependencies:** needs US1's API fields (T025) and fixtures (T027). T035 comes before T036, and T037 is independent.

## Parallel Examples

```text
Foundational:  T003 models.py  |  T005 adapters/common.py
US2 tests:     T007 parse tests  |  T008 load tests  |  T009 roster as-of test
US2 impl:      T010 parse.py  ∥  T012 roster loader default
US1 tests:     T015 engine  |  T017 strategic regression  |  T018 changes
US1 impl:      T019 engine.py  ∥  T020 matchup helpers
US3:           T033 RecordHeadline  |  T034 CategoryTable  |  T038 base.css
```

## Implementation Strategy

1. **Foundation and US2:** the matchup state can be imported from the real file (quickstart §A).
2. **US1 (MVP):** tactical is correct, with base plus remaining games, the opponent from the
   pairing, and no vs or Week. Validate with SC-001 – SC-005.
3. **US3:** the Now score, the week-to-date column, the opponent's roster and the help.
4. **Polish:** style docs, the real-file run and a browser check.
