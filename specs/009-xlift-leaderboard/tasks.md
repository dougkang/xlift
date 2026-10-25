---

description: "Task list for 009 xLift Leaderboard, the Start of Player Analysis"
---

# Tasks: xLift Leaderboard, the Start of Player Analysis

**Input**: Design documents from `/specs/009-xlift-leaderboard/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: included. The constitution's quality gates require core tests, and the spec's success
criteria (SC-001 parity with the picker, SC-002 sums, SC-007 Impact Analysis unchanged) are test
assertions.

**Organization**: tasks are grouped by user story (spec.md):
- US1 (P1): the leaderboard for my team.
- US2 (P2): widening or narrowing the list, including **Evaluate for: League**.
- US3 (P2): navigation between the tools.

The Foundational phase moves the shared xLift code into core (research R1), so the new tool never
imports Impact Analysis. The user's uncommitted edits to `docs/overview.md` and
`docs/tool2-player-comparison.md` are only touched in T040, as research R10 says.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US3 per spec.md

---

## Phase 1: Setup

- [X] T001 Create the feature branch from the current tip of `007-xwcwa-fragility-penalty`: `git switch -c 009-xlift-leaderboard`. Bring along the untracked `specs/008-league-shape-charts/` and `specs/009-xlift-leaderboard/` folders, and the user's uncommitted `docs/` edits, as they are; don't commit them yet. Record the baseline: `uv run pytest -q && uv run lint-imports` in `backend/` and `npm test` in `frontend/` must pass before any change.
- [X] T002 Record the pre-feature numbers for SC-007. Add `backend/tests/integration/test_pre009_snapshot.py` with a single test marked `@pytest.mark.snapshot`. Register the marker in `backend/pyproject.toml`'s `markers`, and add `and not snapshot` to `addopts`, so the normal run skips it.
  - The test uses the `impact_engine` fixture.
  - It calls `analyze(...)` (strategic, default settings) and `list_players(..., free_agents_only=False, limit=200)` for the fixture's first team.
  - It writes `header`, `category_table`, `rosters` (with `xlift`) and the picker's `[player_id, xlift]` to `backend/tests/fixtures/pre009_impact.json`.

  Run it once with the pre-feature code (`uv run pytest -m snapshot`) and commit the JSON. T011 compares against it.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the shared xLift code in core, the per-category breakdown, the independence
contract, and the new tool's skeleton. Every story needs these.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [X] T003 Move the DB-free scenario scoring into core (research R1). Create `backend/src/ffmodel/core/value/scenario.py` with the contents of `backend/src/ffmodel/tools/impact_analysis/value.py`, without `league_spread` and `identity` (they move in T005): `lines`, `team_totals`, `weekly_spread`, `SPREAD_ITERATIONS`, `SPREAD_SEED`, `_out_line` (rename it to the public `out_line`), `score_rows` and `score_pool`.
  - Imports: `ffmodel.core.scenario`, `ffmodel.core.scoring`, `ffmodel.core.sim` and `ffmodel.core.value.xlift` only.
  - Export the public names from `backend/src/ffmodel/core/value/__init__.py`.
  - Move `GAMES_PER_PERIOD = 3` from `backend/src/ffmodel/tools/impact_analysis/settings.py` into `backend/src/ffmodel/core/sim/` (beside `strategic_k`) and export it. `tools/impact_analysis/settings.py` imports it from there, unchanged in value.
- [X] T004 Move the Fragility Penalty into core. Create `backend/src/ffmodel/core/model/fragility.py` with `apply(...)` and `dab_values(...)` from `backend/src/ffmodel/tools/impact_analysis/fragility.py`. `apply` takes the dAB rates from `ffmodel.core.cache.dab` (T005).
- [X] T005 Move the process caches into core. Create `backend/src/ffmodel/core/cache.py` with these parts of `backend/src/ffmodel/tools/impact_analysis/cache.py`:
  - the projection cache: `_cache`, `_priors`, `_latest_run`, `_projection_key`, `projections`;
  - the dAB cache: `_dab`, `dab`. It lazy-imports `dab_values` from `ffmodel.core.model.fragility` inside the function, because `fragility` imports the cache, and core must not import tools;
  - the spread cache: `_spreads`, `spread`;
  - `clear()`, for these caches only;
  - `league_spread(conn, fmt, s, snapshot, prepare=identity)` and `identity`, from `value.py`.

  Add a `typing.Protocol` named `CacheSettings` documenting the attributes the keys read: `league_id`, `as_of`, `window`, `mode`, `remaining`, `fragility`, `games_per_period` (research R5).
- [X] T006 Turn the Impact Analysis modules into thin re-exports, so behavior and imports are unchanged:
  - `backend/src/ffmodel/tools/impact_analysis/value.py` re-exports everything from `ffmodel.core.value.scenario`, plus `league_spread` and `identity` from `ffmodel.core.cache`. It keeps `_out_line = out_line` for existing callers;
  - `backend/src/ffmodel/tools/impact_analysis/fragility.py` re-exports `apply` and `dab_values` from `ffmodel.core.model.fragility`;
  - `backend/src/ffmodel/tools/impact_analysis/cache.py` keeps `original`, `_original` and `ORIGINAL_MAX_KEYS`, and re-exports `projections`, `dab`, `spread` and `MAX_KEYS` from `ffmodel.core.cache`. Its `clear()` clears `_original` and calls `ffmodel.core.cache.clear()`.

  Then search `backend/` and `analysis/` for `monkeypatch` and `mock.patch` targets naming `tools.impact_analysis.value`, `.fragility` or `.cache` attributes that now live in core. Repoint each to the core module so the patch still takes effect (research R1). Run `uv run pytest -q`, `uv run lint-imports` and `cd ../analysis && uv run python xlift_parity.py`: all must pass as before.
- [X] T007 [P] In `backend/tests/unit/test_xlift_by_category.py`, write DB-free tests for T008. Reuse the 4-team synthetic 9cat league style of `backend/tests/unit/test_xlift.py`, and cover:
  - for several candidates, the breakdown's row sums equal `score_candidates` within 1e-9;
  - the result has shape (candidates, `len(fmt.categories)`), in `fmt.categories` order;
  - a candidate with fewer turnovers than the out line has a positive TO value;
  - a high-volume, low-percentage shooter has a negative FG% value while counting categories are positive;
  - equal candidate and out lines give all zeros;
  - results are deterministic.
- [X] T008 In `backend/src/ffmodel/core/value/xlift.py`, add `score_candidates_by_category(team_idx, T, out_line, candidate_lines, fmt, spread) -> np.ndarray` of shape (candidates, categories) (research R2, data-model.md):
  - B[i, c] = Σ_{u≠t} [Φ((k_c(T_t − out + ℓ_i) − k_uc)/s_c) − Φ((k_c(T_t) − k_uc)/s_c)];
  - it is computed like `_wins` but summed over opponents only (`axis=-2`), with the same `_MIN_SPREAD` and NaN-as-coin-flip handling.

  Don't change `score_candidates`. Add the name to `__all__` and to `backend/src/ffmodel/core/value/__init__.py`. Make T007 pass.
- [X] T009 [P] In `backend/.importlinter`, add a contract: `[importlinter:contract:tools-independent]`, `name = Tools must not import each other (Constitution VII)`, `type = independence`, `modules = ffmodel.tools.impact_analysis` and `ffmodel.tools.player_analysis`.
- [X] T010 Create the tool package `backend/src/ffmodel/tools/player_analysis/__init__.py` (docstring: "Player Analysis (Tool 2): find and compare players. 009: the xLift leaderboard."). Create `backend/src/ffmodel/tools/player_analysis/settings.py` with these frozen dataclasses (data-model.md):
  - `PlayerAnalysisSettings`:
    - `league_id: int`, `team_id: int`;
    - `window: int = 82` ("1–82, default 82");
    - `as_of: date | None = None` ("defaults to today");
    - `fragility: str = "dab_tag"` (one of `"none" | "last15" | "dab" | "dab_tag"`);
    - `games_per_period: int = GAMES_PER_PERIOD` (from `ffmodel.core.sim`);
    - `mode: str = "strategic"`, and a `remaining` property that returns `None`;
    - define its own constants. Don't import `tools.impact_analysis`.
  - `LeaderboardQuery`:
    - `evaluate_for: str = "team"` (`team` | `league`);
    - `pool: str = "free_agents"` (`free_agents` | `all`);
    - `top: int | None = 25` ("10–50, multiple of 5, default 25"; `None` = no limit, for Python callers only);
    - `min_games: int = 5` ("1–15, default 5").

  Add a `normalize(s)` that fills `as_of` with today and raises `ValueError` on an unknown fragility.

**Checkpoint**:
- `uv run pytest -q` is green, including `tests/unit/test_xlift_by_category.py`;
- `uv run lint-imports` passes with the new contract;
- `xlift_parity.py` still passes.

---

## Phase 3: User Story 1 - See the best free agents for my team, and why (P1) 🎯 MVP

**Goal**: the Player Analysis page, at `#/player-analysis`, shows the top 25 free agents ranked by
xLift for the selected team. Each has a category-stacked bar and a tick at the net, and the values
equal the Impact Analysis picker's (FR-001, FR-003, FR-006, FR-007, FR-009–FR-015, FR-019–FR-022;
SC-001, SC-002, SC-004, SC-006, SC-007).

**Independent Test**:
- open `#/player-analysis` for a team: 25 free agents in non-increasing xLift order, each with
  stacked segments (negatives left of zero) and a tick at the net;
- a player's net equals the Impact Analysis picker's `xlift` for the same team and settings.

### Tests for User Story 1

- [X] T011 [P] [US1] In `backend/tests/integration/test_leaderboard.py`, add tests on `impact_engine` for `leaderboard(conn, PlayerAnalysisSettings(...), LeaderboardQuery())` (T013), for the fixture's first team:
  - entries are free agents only (`owner_team_id is None`), at most 25;
  - order is `xlift` descending, then `name`, then `player_id`;
  - every entry's `by_category` has `len(categories)` values and sums to `xlift` within 0.01 (SC-002);
  - for every entry, `xlift` equals `list_players(conn, AnalysisSettings(same league, team, window, fragility, as_of), free_agents_only=True, limit=200)`'s `xlift` for that player within 0.005 (SC-001, strategic, no moves);
  - `total` counts every eligible free agent;
  - `footnote` is `"* {found} of {requested} games"` when found < requested, else `None`;
  - `settings.mode == "strategic"`;
  - SC-007: `analyze` and `list_players` still reproduce `tests/fixtures/pre009_impact.json` (from T002) exactly.
- [X] T012 [P] [US1] In `backend/tests/integration/test_api_leaderboard.py`, add API tests with the app's test client (as in the existing `tests/integration/test_api_moves_players.py`) for `POST /api/player-analysis/leaderboard`:
  - 200 with the contracts/api.md shape (`settings`, `evaluate_for`, `team_id`, `team_name`, `categories` with `key`, `label` and `higher_is_better`, `total`, `entries`, `warnings`);
  - 404 for an unknown league or a team not in the league;
  - 422 for `window` 0 or 83, `top` 12 or 55, `min_games` 0 or 16, and an unknown `fragility`, `evaluate_for` or `pool`.

### Implementation for User Story 1

- [X] T013 [US1] Create `backend/src/ffmodel/tools/player_analysis/leaderboard.py` with `leaderboard(conn, settings, query) -> dict` (research R6, data-model.md). Use core imports only:
  1. `s = normalize(settings)`;
  2. `snapshot = get_league(conn, s.league_id)`, raising the tool's own `NotFound(LookupError)` for an unknown league or team, with the same messages as Impact Analysis;
  3. `scenario = from_snapshot(snapshot)`, with no moves;
  4. get the format. On `UnsupportedFormat`, return empty `categories` and `entries`, `total` 0, and the warning `{"code": "UNSUPPORTED_FORMAT", "message": …}`, with the same wording as Impact Analysis;
  5. the pool is `get_player_details(conn, league_id=...) | rostered info` (each rostered player's summary and latest status from the snapshot roster entries). Use these statuses for the Fragility Penalty, so the tag multipliers match the picker's (research R6);
  6. candidates:
     - skip inactive free agents (`not summary.is_active`);
     - skip the selected team's players, and rostered players when `pool == "free_agents"`;
  7. get projections for candidates ∪ rostered via `ffmodel.core.cache.projections` and apply `ffmodel.core.model.fragility.apply(s.fragility, …)`. Get the spread via `ffmodel.core.cache.league_spread(conn, fmt, s, snapshot, prepare)`;
  8. score with `score_pool_by_category` (T014) for `s.team_id`;
  9. drop players without a projection or with `games_found < query.min_games`;
  10. sort by (−xlift, name, player_id), where `xlift = float(sum(by_category))`. `total` = the number left; keep the first `query.top`. In Python, `top=None` keeps every entry, which the parity script needs. The API still enforces 10–50.

  Each entry has `player_id`, `name`, `nba_team`, `owner_team_id`, `owner_label` (the team's name, or `"Free agent"`), `status`, `games_found`, `games_requested`, `footnote`, `xlift` and `by_category` (a list of floats). Also return `settings` (`mode: "strategic"`, `window`, `as_of`, `fragility`), `evaluate_for`, `team_id`, `team_name`, `categories` (`key`, `label`, `higher_is_better` from `fmt.categories`) and `warnings: []`.
- [X] T014 [US1] In `backend/src/ffmodel/core/value/scenario.py`, add `score_pool_by_category(scenario, team_id, pool_projections, fmt, games_per_period, spread, roster_projections) -> dict[int, np.ndarray | None]`. It mirrors `score_pool`, using `out_line` and `score_candidates_by_category`. Export it from `backend/src/ffmodel/core/value/__init__.py`.
- [X] T015 [US1] In `backend/src/ffmodel/api/schemas.py`, add the request and response models (contracts/api.md):
  - `LeaderboardRequest`:
    - `league_id: int`, `team_id: int`;
    - `window: int = Field(82, ge=1, le=82)`, `as_of: date | None = None`, `fragility: Fragility = "dab_tag"`;
    - `evaluate_for: Literal["team", "league"] = "team"`, `pool: Literal["free_agents", "all"] = "free_agents"`;
    - `top: int = Field(25, ge=10, le=50, multiple_of=5)`, `min_games: int = Field(5, ge=1, le=15)`;
  - `LeaderboardSettings` (`mode: Literal["strategic"]`, `window`, `as_of: date`, `fragility`);
  - `LeaderboardCategory` (`key`, `label`, `higher_is_better`);
  - `LeaderboardEntry` (the fields in T013, with `nba_team: str | None`, `owner_team_id: int | None`, `footnote: str | None`, `xlift: float`, `by_category: list[float]`);
  - `Leaderboard` (`settings`, `evaluate_for`, `team_id`, `team_name`, `categories`, `total`, `entries`, `warnings: list[WarningModel]`).
- [X] T016 [US1] In `backend/src/ffmodel/api/routes.py`, add `POST /api/player-analysis/leaderboard` (`response_model=schemas.Leaderboard`). It builds `PlayerAnalysisSettings` and `LeaderboardQuery` from the request and calls `leaderboard`, mapping the tool's `NotFound` to 404 in `_run` (alongside Impact Analysis's). Keep the handler thin. Make T011 and T012 pass.
- [X] T017 [P] [US1] Add the hash route hook `frontend/src/state/route.ts`. It exports `type Route = "impact" | "player-analysis"` and `useRoute(): Route`, mapping `#/player-analysis` to `"player-analysis"` and anything else to `"impact"`, listening to `hashchange` (research R8).
- [X] T018 [P] [US1] Add `frontend/src/state/playerAnalysis.ts`: a reducer and a `usePlayerAnalysis()` hook for `{ evaluateFor: "team" | "league", pool: "free_agents" | "all", top: number, minGames: number }`, defaults `team`, `free_agents`, 25 and 5. It persists to `sessionStorage` key `"ffm.player-analysis.v1"`, wrapped in try/catch like `frontend/src/state/scenario.ts`, and falls back to each default for a missing or invalid stored value ("top: 10–50, multiple of 5"; "minGames: 1–15").
- [X] T019 [US1] Create `frontend/src/Shell.tsx`, which owns `useScenario()` and `useRoute()`. It renders `<App state dispatch />` for `"impact"` and `<PlayerAnalysis state dispatch />` for `"player-analysis"` (the nav is added in US3). Change `frontend/src/App.tsx` to take `state` and `dispatch` as props instead of calling `useScenario()`, keeping its existing exports (`toRequest`, the default export). Render `Shell` in `frontend/src/main.tsx`. Update the existing frontend tests that render `<App />` to render it with `useScenario`-backed props, or through `Shell`.
- [X] T020 [US1] In `frontend/src/api/client.ts`, add `leaderboard(req, signal)` posting to `/api/player-analysis/leaderboard`, with the same error handling as `analyze`, and export the `Leaderboard`, `LeaderboardEntry` and `LeaderboardRequest` types. Regenerate `frontend/src/api/schema.d.ts` with `npm run gen:api` (needs `ffm serve` running), or hand-add the types if the server can't run.
- [X] T021 [US1] In `frontend/src/components/Controls.tsx`, add an optional `showReset = true` prop. When false, the Reset row isn't rendered.
- [X] T022 [US1] Create `frontend/src/player-analysis/Leaderboard.tsx` with Observable Plot (contracts/ui.md "Chart", research R9). It takes `categories` and `entries` and only draws them, with no ranking or arithmetic beyond formatting:
  - **Rows**: one per entry in the given order, about 18px each, with `y` a band of player ids in entry order.
  - **Bars**: `Plot.barX` on the long data (entry × category) with Plot's stack transform (`x` = value, `y` = player, `fill` = category index, default offset), so positive segments stack right of 0 and negative ones left.
  - **Colors**: the style guide's qualitative palette in category order: `#a6cee3`, `#1f78b4`, `#b2df8a`, `#33a02c`, `#fb9a99`, `#e31a1c`, `#fdbf6f`, `#ff7f00`, `#cab2d6` (updated after implementation).
  - **Tick**: `Plot.tickX` at `xlift`, drawn as a 4px `#fff` tick under a 2px `#111` one.
  - **Zero rule**: `Plot.ruleX([0])` in `#ccc`.
  - **Axis**: x at the top, label "Weekly category wins added", no grid.
  - **Font**: Helvetica Neue.
  - **Tooltips**: `title` "Player · Category · +0.31" on segments and "Player · xLift +1.84" on the tick (two decimals, real minus sign `−`).
  - **Row labels**: in an HTML column to the left of the plot, aligned to the same row height: the name in bold; the owner, muted; the status in red (as `Roster.tsx` shows it); and the right-aligned signed net, then `*` when `footnote` is set.
  - **Legend**: swatches with category labels, above the chart.
  - **Empty**: when `entries` is empty, render "No players match these filters." instead of the chart.
- [X] T023 [US1] Create `frontend/src/player-analysis/PlayerAnalysis.tsx` (contracts/ui.md "Page"):
  - **Header**: the masthead "Player Analysis", then the explainer "Find the players worth adding: who adds the most weekly category wins, and in which categories.", then a section rule.
  - **Data**: load leagues and the league detail the way `App.tsx` does.
  - **Shared controls**: `<Controls showReset={false} />` (window, Fragility Penalty, league, team), dispatching only `setLeague`, `setTeam`, `setWindow` and `setFragility`. Never send moves, and never dispatch `setMode`.
  - **Leaderboard section**: the "XLIFT LEADERBOARD" divider with `<HelpButton topic="leaderboard" />`; the scope line "Scored for {team_name}"; "{entries.length} of {total} players"; then `<Leaderboard />`; then the footnotes list.
  - **Requests**: debounced at 250 ms with an AbortController, as in `App.tsx`. The request is `{league_id, team_id, window, fragility, evaluate_for, pool, top, min_games}` from the shared and Player Analysis state. Show the pending style (italic, 75% opacity) while in flight, and errors in the `error` style.

  The Evaluate for, Pool, Show top and Min games controls are US2 (T029). Until then, the request uses the stored defaults.
- [X] T024 [US1] In `frontend/src/help/content.ts`, add the `leaderboard` topic to `TopicId` and `HELP`, using contracts/ui.md's wording: **Reading it** and the shared `XLIFT` term. Stay within 120 words, with no file names.
- [X] T025 [P] [US1] In `frontend/tests/leaderboard.test.tsx`, with a mocked `leaderboard` response fixture `frontend/tests/fixtures/leaderboard.json` (three entries, one with a negative FG% segment and a footnote), test that:
  - rows render in the fixture's order, with name, owner and the signed net (`−` for negatives);
  - a negative segment is drawn left of the zero rule (its x extent is below the zero position);
  - the legend lists every category label;
  - an empty `entries` shows "No players match these filters.";
  - the page sends no `moves` and no `mode`;
  - adjacent categories' fills differ, and with the fixture's x domain, a 0.10 segment renders at least 4px wide (SC-006).
- [X] T026 [US1] Run `uv run pytest -q`, `uv run lint-imports` and `npm test`. All pass.

**Checkpoint**: `#/player-analysis` shows the team-scored free-agent leaderboard (the MVP).

---

## Phase 4: User Story 2 - Widen or narrow the list (P2)

**Goal**: the Pool, Show top, Min games and Evaluate for controls (FR-008, FR-016–FR-018; SC-003,
SC-004, SC-005).

**Independent Test**:
- **All players** adds rostered players with their team labels;
- **Show top** sets the count;
- **Min games** hides short projections;
- **League** ranks by the league average, which doesn't change with the selected team.

### Tests for User Story 2

- [X] T027 [P] [US2] In `backend/tests/unit/test_league_scope.py`, write DB-free tests for T028 on the synthetic 4-team league:
  - a free agent's league breakdown equals the per-category mean of `score_pool_by_category` over all 4 teams;
  - a rostered player's equals the mean over the 3 teams other than their owner;
  - each team uses its own `out_line` (an open active slot on one team gives that team a zero out line);
  - row sums equal the mean of the per-team nets within 1e-9;
  - the result doesn't depend on any selected team.
- [X] T028 [US2] In `backend/src/ffmodel/core/value/scenario.py`, add `score_league_by_category(scenario, pool_projections, fmt, games_per_period, spread, roster_projections) -> dict[int, np.ndarray | None]` (research R3):
  - for each team, compute its own `out_line` and `score_candidates_by_category` for all candidates;
  - set the owner's row to NaN (`scenario.owner`);
  - take the `np.nanmean` over teams, inside `warnings.catch_warnings()`.

  Export it from `backend/src/ffmodel/core/value/__init__.py`. Make T027 pass.
- [X] T029 [P] [US2] In `backend/tests/integration/test_leaderboard.py`, add tests:
  - `pool="all"` includes rostered players with `owner_label` = their team's name, never the selected team's under `evaluate_for="team"`;
  - `top` 10 gives exactly 10 entries (or `total` if fewer), and the first 10 equal the first 10 at `top` 25;
  - `min_games` drops every entry with `games_found < min_games`, and a `min_games` above every player's games gives `entries == []`, `total == 0`;
  - `evaluate_for="league"`:
    - values equal T028's for the same projections;
    - with `pool="all"`, the selected team's players are included;
    - changing `team_id` leaves every entry's `xlift` unchanged;
    - `by_category` still sums to `xlift`.

### Implementation for User Story 2

- [X] T030 [US2] In `backend/src/ffmodel/tools/player_analysis/leaderboard.py`, branch on `query.evaluate_for`:
  - `"league"` scores with `score_league_by_category` and doesn't skip the selected team's players (FR-016);
  - `"team"` stays as T013 has it.

  Make T029 pass.
- [X] T031 [US2] In `frontend/src/player-analysis/PlayerAnalysis.tsx`, add the leaderboard controls row (contracts/ui.md "Controls"):
  - **Evaluate for** (Your team | League) and **Pool** (Free agents | All players) as `pill` radio buttons (`role="radio"`, `aria-checked`), styled like the radar-scale pills;
  - **Show top** as a select of 10–50 in steps of 5, and **Min games** as a select of 1–15;
  - `<HelpButton topic="playerAnalysisSettings" />` at the row's right.

  These are wired to `usePlayerAnalysis()`. Under League, the scope line reads "Averaged over every team but the player's own".
- [X] T032 [US2] In `frontend/src/help/content.ts`, add the `playerAnalysisSettings` topic with contracts/ui.md's **Controls** wording (Evaluate for, Pool, Show top, Min games, Last and Fragility Penalty), within 120 words and without file names.
- [X] T033 [P] [US2] In `frontend/tests/leaderboard.test.tsx`, test that:
  - changing each control sends the matching `evaluate_for`, `pool`, `top` and `min_games`;
  - the League scope line shows;
  - the settings persist to `ffm.player-analysis.v1`, and an invalid stored `top` (e.g. 12) falls back to 25.
- [X] T034 [US2] In `analysis/xlift_parity.py`, add the 009 checks under Last 15 (research R4):
  - **Your team**: `leaderboard(..., LeaderboardQuery(evaluate_for="team", pool="free_agents", top=None, min_games=1))` for the first team, against `np.nansum(defs["rgp"][ti], axis=1)`, over the shared free agents. PASS ≤ 0.05.
  - **League**: the same call with `evaluate_for="league"`, its values against `np.nansum(np.nanmean(defs["rgp"], axis=0), axis=1)` for free agents. Print the teams with open active slots (`scenario.open_active_slots(t) > 0`). If there are any, report the max difference over all teams and, as the PASS criterion, over the notebook and app averages restricted to teams without open slots. PASS ≤ 0.05.

  Exit nonzero on a FAIL, keeping the existing SC-001 and SC-005 checks.

**Checkpoint**: every leaderboard control works, and both scopes match the notebook.

---

## Phase 5: User Story 3 - Move between the two tools (P2)

**Goal**: a plain-text nav on both tools, with settings carried over, moves ignored with a note,
and the mode kept (FR-002, FR-004, FR-005).

**Independent Test**: from Impact Analysis, go to Player Analysis and back. League, team, window
and Fragility Penalty are kept. Impact Analysis's moves and tactical mode are still there, and
Player Analysis shows the moves note.

- [X] T035 [P] [US3] Create `frontend/src/components/Nav.tsx` (contracts/ui.md "Navigation"): a `<nav aria-label="Tools">` with hash links "Impact Analysis" (`#/`) and "Player Analysis" (`#/player-analysis`). The text is ALL CAPS, the current link is bold and underlined with `aria-current="page"`, and the other is muted `#555`, black on hover. No borders, pills or backgrounds. Add its CSS in `frontend/src/styles/base.css`.
- [X] T036 [US3] In `frontend/src/Shell.tsx`, render `<Nav current={route} />` above the current tool's masthead on both tools.
- [X] T037 [US3] In `frontend/src/player-analysis/PlayerAnalysis.tsx`, when `state.moves.length > 0`, show the muted line "The leaderboard uses rosters as they are, without your Impact Analysis moves." under the controls.
- [X] T038 [P] [US3] In `frontend/tests/shell.test.tsx`, test that:
  - the nav renders on both routes and marks the current one;
  - switching `location.hash` swaps tools;
  - league, team, window and fragility chosen in Impact Analysis are what Player Analysis requests;
  - with a move and tactical mode set in Impact Analysis, Player Analysis shows the moves note, sends no moves, and returning to `#/` still has the move and tactical mode.

**Checkpoint**: both tools are linked and share settings.

---

## Phase 6: Polish & cross-cutting

- [X] T039 [P] Amend `docs/style.md`. Add a "Leaderboard (stacked bars)" section under Visualizations covering:
  - one row per player in server order;
  - segments in the qualitative palette by category order, with no borders;
  - negatives left of a `#ccc` zero rule;
  - the net tick, `#111` 2px over a 4px white halo;
  - row labels (bold name, muted owner, signed net with a real minus sign);
  - the legend above.

  Add to the Layout section: "Tool nav: plain-text ALL CAPS links above the masthead; the current tool bold and underlined."
- [X] T040 [P] Update the Tool 2 docs (research R10). These are the user's uncommitted files, so edit only the named lines and keep everything else as it is.
  - In `docs/tool2-player-comparison.md` (title "Tool 2: Player Analysis"), add a "## xLift leaderboard" section in plain words:
    - what each bar, segment and tick shows;
    - Evaluate for (Your team / League);
    - Pool, Show top and Min games;
    - that it uses rosters without Impact Analysis moves.
  - In `docs/overview.md`, change Tool 2's entry to `[Player Analysis](tool2-player-comparison.md)`. Keep its description unless the user says otherwise.
- [X] T041 Run quickstart §3 (performance) on the real league with the caches cleared (`ffmodel.tools.impact_analysis.cache.clear()`). Time `leaderboard(...)` cold for `evaluate_for` "team" and "league": each < 3 s (SC-005). If League is over, profile `score_league_by_category` first. Batch all teams in one vectorized call before anything else.
- [X] T042 Run the full gates:
  - in `backend/`: `uv run pytest -q`, `uv run ruff check src tests`, `uv run ruff format --check src tests` and `uv run lint-imports`;
  - in `frontend/`: `npm test` and `npm run build`, so `ffm serve` without `--reload` gets the new UI;
  - `cd analysis && uv run python xlift_parity.py`.

  All pass.
- [X] T043 Walk through quickstart §4 in the app (`ffm serve --reload`), steps 1–9, and note any difference from the expected results.

---

## Dependencies & execution order

- **Setup (T001–T002)** → **Foundational (T003–T010)** → stories.
  - Within Foundational: T003 → T004 → T005 → T006 (the move, in order). T007 and T009 can run any time. T008 needs T003. T010 needs nothing else.
- **US1 (T011–T026)** depends on Foundational. It's the MVP.
  - Backend: T014 → T013 → T015 → T016.
  - Frontend: T017 and T018 → T019 → T020 → T021–T024.
- **US2 (T027–T034)** depends on US1's tool module (T013) and page (T023), because it extends them. T034 needs T030.
- **US3 (T035–T038)** depends on US1's Shell (T019) and page (T023). It's independent of US2.
- **Polish**: T039 and T040 can run any time after US1. T041–T043 come last.

## Parallel opportunities

- T007 and T009 alongside the move (T003–T006).
- In US1: T011 and T012 (backend tests) together; T017 and T018 (frontend state) together; the backend chain (T013–T016) alongside the frontend chain (T017–T024) once T015's field names are fixed; T025 after T022.
- In US2: T027 and T029 together; T031–T033 (frontend) alongside T028 and T030 (backend).
- US3 (T035–T038) alongside US2.
- T039 and T040 together.

### Example: US1 in parallel

```text
T011 leaderboard integration tests     T012 API tests
T014 → T013 → T015 → T016 (backend)    T017 + T018 → T019 → T020 → T021–T024 (frontend)
```

## Implementation strategy

1. **MVP**: Setup → Foundational → US1. The team-scored free-agent leaderboard at
   `#/player-analysis`, equal to the picker's values.
2. **US2**: the controls and League scope, with notebook parity for both scopes.
3. **US3**: the nav, carried settings and the moves note.
4. **Polish**: the style amendment, Tool 2 docs, performance and gates.
