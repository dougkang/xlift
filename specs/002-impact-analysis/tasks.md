---

description: "Task list for Impact Analysis Tool"
---

# Tasks: Impact Analysis Tool

**Input**: Design documents from `specs/002-impact-analysis/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (api.md, scoring-format.md, ui.md), quickstart.md

**Tests**: Included. The constitution's quality gates require tests for ratio aggregation,
lower-is-better, outcomes with ties, fixed-seed determinism, distinct tactical and strategic
computations, and format conformance. Write each story's tests first and confirm they fail.

**Organization**: Tasks are grouped by user story. US1 (strategic standing) and US2 (moves) are
both P1. US3 (tactical) is P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story the task belongs to (US1–US3)

## Conventions for every task

- **Backend**:
  - Code lives in `backend/src/ffmodel/` and tests in `backend/tests/`.
  - Run everything from `backend/` with `uv run …`.
  - SQL goes through SQLAlchemy Core `text()` only.
- **Frontend**:
  - Code lives in `frontend/src/` and tests in `frontend/tests/`.
  - It needs **Node 22 LTS**, which isn't installed yet. Ask the user before running
    `brew install node@22`.
- **Layering** (Constitution VII; import-linter contracts from T002):
  - `core` must not import `tools`, `api` or `adapters`;
  - `tools` must not import `api` or `adapters`;
  - `api` imports `tools` and `core`;
  - `cli.py` is the only module that may import everything.
- **Frontend has no domain rules**: it does no statistics and applies no roster rules. Every
  number, every enabled or disabled state, and every curve comes from the API.
- **Category list**: the 9cat categories appear only in `core/scoring/nine_cat.py`. Every other
  module iterates `fmt.categories` (Constitution II).
- **Regular season only** (FR-012): every read goes through `core.data` functions that already
  filter on it.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Update `backend/pyproject.toml`:
  - Add runtime dependencies `numpy>=2.0`, `fastapi>=0.115`, `uvicorn[standard]>=0.30`.
  - Add `httpx>=0.27` to the dev group.
  - Add the pytest marker `"slow: real-database timing and stability checks (manual)"`.
  - Change `addopts` to `-m 'not live and not slow'`.

  Then run `uv sync`.
- [X] T002 [P] Extend `backend/.importlinter` with three `forbidden` contracts:
  1. `ffmodel.core` → `ffmodel.tools`, `ffmodel.api`
  2. `ffmodel.tools` → `ffmodel.api`, `ffmodel.adapters`
  3. `ffmodel.adapters` → `ffmodel.tools`, `ffmodel.api`

  Keep the 3 existing contracts.
- [X] T003 [P] Create the packages, each with an empty `__init__.py`:
  - `backend/src/ffmodel/core/scoring/`
  - `backend/src/ffmodel/core/model/`
  - `backend/src/ffmodel/core/sim/`
  - `backend/src/ffmodel/core/scenario/`
  - `backend/src/ffmodel/tools/`
  - `backend/src/ffmodel/tools/impact_analysis/`
  - `backend/src/ffmodel/api/`

  Also create the test directories `backend/tests/scoring/` and `backend/tests/slow/`, each with
  an `__init__.py`.
- [X] T004 Scaffold `frontend/` (requires Node 22).
  - **`package.json`**:
    - Dependencies, pinned to exact versions resolved from npm at install time: `react`,
      `react-dom` (19.x), `d3-scale`, `d3-shape`, `@observablehq/plot`.
    - Dev dependencies: `vite`, `@vitejs/plugin-react`, `typescript` (5.x), `vitest`,
      `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `openapi-typescript`,
      `@types/react`, `@types/react-dom`, `@types/d3-scale`, `@types/d3-shape`.
    - Scripts:
      - `dev`: `vite`
      - `build`: `tsc -b && vite build`
      - `test`: `vitest run`
      - `gen:api`: `openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts`
  - **`vite.config.ts`**: React plugin; `server.proxy['/api'] = 'http://localhost:8000'`;
    Vitest `environment: 'jsdom'`.
  - **`tsconfig.json`**: strict.
  - **`index.html`** with `<title>Impact Analysis</title>`, plus `src/main.tsx`.
  - Add `frontend/node_modules/` and `frontend/dist/` to the root `.gitignore`.
- [X] T005 [P] Create `frontend/src/styles/tokens.css` and `frontend/src/styles/base.css` from
  `docs/style.md` and research R9:
  - **Font**: `font-family: "Helvetica Neue", Helvetica, Arial, sans-serif` everywhere.
  - **Color tokens**:
    - `--ink:#111`, `--paper:#fff`, `--yours:#f5c518`, `--danger:#c00`
    - `--muted:#555`, `--rule:#ccc`, `--hover:#eee`
    - `--sel:#1C324A`, `--other:#9DC0F5`, `--opp:#A96043`, `--leader:#CE7955`, `--avg:#898240`
  - **Shapes and effects**: no `border-radius`, `box-shadow` or gradients.
  - **Buttons**: a `<button>` has a 1px solid `#111` border. A destructive button has a red
    border and red text, and fills red on hover.
  - **Text styles**: masthead ~3rem weight 900 with a 4px rule; section dividers in ALL CAPS;
    table data 0.78rem.
  - **Pending state**: `.pending { font-style: italic; opacity: .75 }`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: scoring formats, the bulk reads, player projections, the simulation engine, the base
scenario, the test fixture, the API shell, and the frontend shell. Every story needs these.

**⚠️ CRITICAL**: no story work starts until this phase is complete.

### Scoring formats (Constitution II)

- [X] T006 Implement `backend/src/ffmodel/core/scoring/base.py` exactly per
  `contracts/scoring-format.md`:
  - **`Category`**, a frozen dataclass:
    - fields: `key`, `label`, `kind: Literal["additive","ratio"]`, `stat`, `numerator`,
      `denominator`, `higher_is_better=True`, `decimals=0`
    - `__post_init__` validates that "`kind=ratio` requires a numerator and denominator", and
      that additive requires `stat`
  - **`ScoringFormat`**, a base class providing `category_values`, `compare`, `matchup`,
    `projected_average`:
    - `category_values`: ratio = Σ numerator / Σ denominator per iteration, NaN when the
      denominator is 0
    - `compare`: returns `int8` values in {+1, 0, −1}, honors `higher_is_better`, and treats NaN
      on either side as 0
    - `matchup`: `sign(wins − losses)`
    - `projected_average`: additive = mean; ratio = mean(numerator) / mean(denominator)
  - **Registry**: `UnsupportedFormat(Exception)`, `register(fmt)`, `get_format(id)`,
    `available_formats()`.
- [X] T007 Implement `backend/src/ffmodel/core/scoring/nine_cat.py`: register `9cat_h2h` with the
  9 categories in the table in `contracts/scoring-format.md`, in that order.
  - Categories: pts, reb, ast, stl, blk, fg3m, fg_pct (fgm/fga, 3 decimals), ft_pct (ftm/fta,
    3 decimals), and tov (`higher_is_better=False`).
  - `base_stats = ("fgm","fga","fg3m","ftm","fta","reb","ast","stl","blk","tov")`.
  - `derived_stats = {"pts": 2·fgm + fg3m + ftm}`.

  Import it from `core/scoring/__init__.py` so it registers on import.
- [X] T008 [P] Write `backend/tests/scoring/test_conformance.py`, parametrized over
  `available_formats()`, with the 8 checks in `contracts/scoring-format.md`:
  1. Base stats exist in the 001 `player_game` columns.
  2. Shapes; ratios are exactly Σ numerator / Σ denominator.
  3. A zero denominator gives NaN, and NaN compares as a tie.
  4. Antisymmetry, and `compare(a, a) == 0`.
  5. Direction, including TO (the lower total wins).
  6. `matchup` values are in {+1, 0, −1} and antisymmetric.
  7. Ratio of means differs from the mean of ratios on the example where the makes/attempts
     pairs are (1/1, 9/19), giving 10/20 = .500 against .737.
  8. Unknown format raises.

### Bulk reads (`core/data`)

- [X] T009 Implement `backend/src/ffmodel/core/data/bulk.py` and export its functions from
  `core/data/__init__.py`:
  - **`get_last_n_games_bulk(conn, player_ids, n, *, as_of) -> dict[int, GameWindow]`**: one
    query using `ROW_NUMBER() OVER (PARTITION BY pg.player_id ORDER BY g.game_date DESC,
    g.game_id DESC)`, regular season, `game_date <= as_of`. Every requested player gets a
    `GameWindow`, including `found = 0`.
  - **`count_team_games_bulk(conn, player_ids, start, end, *, statuses) -> dict[int, int]`**: the
    001 `count_team_games` logic for many players in one query.
  - **`get_data_freshness(conn, league_id) -> DataFreshness`**: `nba_data_loaded_at` is the
    latest `finished_at` of `load_run WHERE source='nba_stats' AND outcome='succeeded'`, or None.
    `roster_as_of` is the max `player_status.as_of` among the league's rostered players. Add the
    `DataFreshness` dataclass to `core/data/models.py`.
- [X] T010 [P] Write `backend/tests/integration/test_core_bulk.py` against the 001 fixture
  (`fixture_engine`):
  - `get_last_n_games_bulk` equals the per-player `get_last_n_games` for every fixture player,
    with n = 15 and `as_of = FIXTURE_TODAY`. This covers the 4 + 11 window, "3 of 15", and 0
    games.
  - `count_team_games_bulk` equals per-player `count_team_games` for both status sets.
  - Freshness: `nba_data_loaded_at` is None when no `load_run` row exists, and `roster_as_of` is
    `2026-10-29`.

### Player projections (`core/model`)

- [X] T011 Implement `backend/src/ffmodel/core/model/projection.py`:
  - **`PlayerProjection`**, a frozen dataclass:
    - `player_id`, `games_found`, `games_requested`
    - `mean: ndarray`, `chol: ndarray | None`, `mean_stderr: ndarray`
    - `availability: float | None`, `games_remaining: int`
    - property `is_short`
  - **`fit_projection(window, base_stats, *, shrink_k=5) -> PlayerProjection`**, per research R1:
    - X is the n × d matrix of `base_stats` from `window.games`; μ is its column mean.
    - S is the sample covariance (zeros when n < 2).
    - D = diag(max(μ, 0.25)).
    - λ = k / (max(n − 1, 0) + k).
    - Σ = (1 − λ)S + λD, and `chol = cholesky(Σ + 1e-9 I)`.
    - `mean_stderr = sqrt(diag(Σ) / n)`.
    - When n = 0: `chol = None` and `mean` is zeros.
  - **`availability_rate(games_played, team_games) -> float | None`**: None when games_played is
    0; 1.0 when team_games is 0; otherwise `min(1, played / team_games)`.
  - **`build_projections(conn, player_ids, fmt, *, window, as_of, period=None) -> dict[int,
    PlayerProjection]`**:
    - windows come from `get_last_n_games_bulk`;
    - availability comes from `get_availability` over [the oldest game date in the window,
      `as_of`] (research R4);
    - `games_remaining` comes from `count_team_games_bulk(statuses=("scheduled",))` over
      [`as_of`, `period_end`] when a period is given, and is 0 otherwise.
- [X] T012 [P] Write `backend/tests/unit/test_projection.py`:
  - μ and S on a hand-built 3-game window.
  - λ = 5/7 when n = 3, and λ = 1 when n = 1 (Σ = D).
  - The Cholesky factor exists for n = 1 and n = 2 (rank-deficient S).
  - n = 0 gives `chol` None and `is_short`.
  - `availability_rate` cases: (0, x) → None; (5, 0) → 1.0; (6, 10) → 0.6; (11, 10) → 1.0.
- [X] T013 [P] Write `backend/tests/integration/test_projection_db.py` (001 fixture, `as_of =
  FIXTURE_TODAY`):
  - Iggy Injured's availability over his window is 2 / 4 = 0.5.
  - Dončić has 15 games found.
  - Dybantsa is short (3 of 15).
  - With period 2026-10-31 → 2026-11-08 and `as_of = 2026-10-31`, Iggy's `games_remaining` is 3.

### Simulation engine (`core/sim`)

- [X] T014 Implement `backend/src/ffmodel/core/sim/engine.py`, per research R2 and R3:
  - **`simulate_team(projections, k_sampler, fmt, *, iterations, seed, mode_code) -> TeamSamples`**:
    - for each projection with `chol` not None: `rng = np.random.default_rng([seed, player_id,
      mode_code])`, `k = k_sampler(proj, rng, iterations)`, `z = rng.standard_normal((iterations,
      d))`, and raw = k·μ + √k·(z @ cholᵀ);
    - sum the raw values into team totals;
    - apply validity to the **team** totals: floor at 0, round to an integer, then
      fgm = min(fgm, fga), fg3m = min(fg3m, fgm), ftm = min(ftm, fta) (generically: for each ratio
      category, numerator ≤ denominator; plus `fg3m ≤ fgm` declared in the format as
      `subset_constraints`);
    - add the derived stats.
  - **k samplers**:
    - `strategic_k(G=3)`: Binomial(G, availability); `availability = None` gives 0.
    - `tactical_k`: the constant `games_remaining`.
  - **`category_values(team_samples, fmt)`** → (iterations, n_categories).
  - **`matchup_odds(a, b, fmt) -> MatchupOdds`**: per category `(p_win, p_tie, p_loss)` plus the
    matchup triple.
  - **`projected_averages`**, and **`ranks(averages_by_team, fmt)`**: competition ranking with
    direction applied (1 = best).
  - **`record(odds_list, unit)`**: W/L/T using the more-than-half rule (spec FR-014).
- [X] T015 [P] Implement `backend/src/ffmodel/core/sim/curves.py` with
  `density_curves(samples_by_role, *, points=96, subsample=2000, seed)`:
  - one shared grid from the 0.5th to the 99.5th percentile of all series;
  - a Gaussian KDE with Scott's bandwidth;
  - NaN values are dropped;
  - a degenerate series (zero variance) gets a narrow spike at its value.

  Return `{x, series:{role: density}}` (research R6).
- [X] T016 [P] Write `backend/tests/unit/test_engine.py`, using synthetic `PlayerProjection`s with
  no DB:
  - **SC-006**: for every iteration, the FG% and FT% category values equal the team totals
    fgm / fga and ftm / fta, and are NaN when fga = 0 (a team with all fga means 0).
  - **SC-005**: team A's players are 30% better than B, C and D's in every stat and 30% *lower*
    in TO. A's strategic record against B, C and D is 3–0–0, and A is rank 1 in all 9 categories,
    including TO.
  - **Ties**: two identical teams with the same seed stream have p_tie = 1 in every category and
    a matchup tie.
  - **SC-002**: the same inputs and seed give identical arrays; a different seed gives different
    arrays.
  - **Common random numbers**: replacing one player on team A leaves team B's samples
    bit-identical.
  - **No clipping bias**: 10 players at 0.3 BLK per game with k = 3 have a team BLK mean within
    1% of 9.0.
  - **Strategic k**: availability 0.5 with G = 3 averages 1.5 games per iteration (±2%).
  - **Ranks**: competition ranking on (10, 8, 8, 5) gives (1, 2, 2, 4), and TO is reversed.
  - **Record rule**: p_win = 0.5 exactly counts as a tie.
- [X] T017 [P] Write `backend/tests/unit/test_curves.py`:
  - each density integrates to about 1 (trapezoid rule, ±5%) over the grid;
  - the shared grid covers every series;
  - zero-variance input gives a spike without dividing by zero;
  - the result is deterministic for a given seed.

### Base scenario (`core/scenario`)

- [X] T018 Implement `backend/src/ffmodel/core/scenario/scenario.py`:
  - **`Scenario`**, a frozen dataclass:
    - `league: LeagueSettings`
    - `rosters: Mapping[team_id, tuple[RosterSpot, ...]]`, where `RosterSpot(player_id, slot)`
    - `base_reserve: frozenset[player_id]`
    - property `owner`: a map from player_id to team_id
  - **`from_snapshot(snapshot) -> Scenario`**.
  - **`active_count(team_id)`**, **`open_active_slots(team_id)`**, and
    **`check_invariants()`**, per data-model.md:
    - active count ≤ `active_roster_capacity`;
    - a player is on at most one team;
    - reserve slots hold only `base_reserve` players.

  Move transitions are added in US2 (T034).

### Test fixture for tool and API tests

- [X] T019 Create `backend/tests/fixtures/impact_dataset.py` with `load_impact_fixture(conn)` and
  `IMPACT_TODAY = date(2026, 11, 18)`, a Wednesday whose week is Mon 11-16 to Sun 11-22. It
  writes through the 001 schema only and is independent of `dataset.py`:
  - **Seasons**: `2026-27` (2026-10-20 → 2027-04-11).
  - **NBA teams**: 1 BOS, 2 MIA, 3 NYK, 4 CHI.
  - **Final games**, every day from 2026-10-20 to 2026-11-17. For day index d:
    - d % 3 == 0: BOS–MIA, NYK–CHI
    - d % 3 == 1: BOS–NYK, MIA–CHI
    - d % 3 == 2: BOS–CHI, MIA–NYK

    Every team plays every day.
  - **Scheduled games**:
    - 11-18 BOS–CHI, 11-19 BOS–MIA, 11-20 BOS–NYK, 11-21 BOS–CHI, 11-22 NYK–CHI;
    - a `postponed` game on 11-21, MIA–NYK.

    Games remaining from 11-18 through 11-22: BOS 4, CHI 3, NYK 2, MIA 1.
  - **Players** (internal IDs 1–16), each with a strength s and an NBA team. Each player's box
    score in game g is base × s × (1 + 0.25·sin(1.7·g + player_id)), rounded, where
    base = {fga 15, fgm 7, fg3a 6, fg3m 2, fta 5, ftm 4, oreb 1, dreb 5, ast 5, stl 1, blk 1,
    tov 2, pf 2, minutes 30}. Then enforce:
    - fgm ≤ fga, fg3m ≤ fgm, fg3a ≤ fga, fg3a ≥ fg3m, ftm ≤ fta;
    - reb = oreb + dreb;
    - pts = 2·fgm + fg3m + ftm.
  - **Rosters** for league `impact-league` (capacity 3, `9cat_h2h`):
    - `t.A` "Alphas" (Ann): Alpha One (BOS, s 1.5), Alpha Two (NYK, 1.5), Alpha Three (CHI, 1.5)
    - `t.B` "Betas" (Bo): Beta One (MIA, 1.0), Beta Two (BOS, 1.0), Beta Three (NYK, 1.0)
    - `t.C` "Gammas" (Cy): Gamma One (CHI, 1.0) active, Gamma Two (MIA, 1.0) active, and Gamma
      Hurt (NYK, 2.0) **reserve**, status `IL`. Gammas has 1 open active slot.
    - `t.D` "Deltas" (Di): Delta One/Two/Three (BOS/MIA/CHI, 0.6)
  - **Free agents**:
    - Steady Streamer (MIA, 1.0): 1 game left
    - Busy Streamer (BOS, 0.9): 4 games left
    - Rookie Ray (CHI, 1.0): only 2 final games (11-16 and 11-17), status `Q`
    - Bench Ben (NYK, 0.3)
  - **Appearances**: every player except Rookie Ray appears in every final game of their team.
  - **Stints**: every player has an open stint from 2026-10-20 on their team.
  - **`player_status`** (source `yahoo`, `as_of` 2026-11-18): Gamma Hurt `IL`, Rookie Ray `Q`,
    everyone else `healthy`.
  - **`load_run`**: one `nba_stats` `succeeded` row with `finished_at
    2026-11-18T08:00:00+00:00`.
  - Export the player ID constants.
- [X] T020 Add an `impact_engine` fixture (a migrated DB plus `load_impact_fixture`) to
  `backend/tests/conftest.py`, and write `backend/tests/integration/test_impact_fixture.py`:
  - `assert_contract_invariants` passes;
  - games remaining per team for 11-18…11-22 are BOS 4, CHI 3, NYK 2, MIA 1;
  - Gammas has 1 open active slot.

### API shell and CLI

- [X] T021 Implement `backend/src/ffmodel/api/schemas.py` with the Pydantic v2 models in
  `contracts/api.md`:
  - **`ScenarioRequest`**, with these validators:
    - `window` 1–82
    - `iterations` 1,000–50,000
    - `period_start ≤ period_end`
    - `opponent_id != team_id`
    - `moves` is a list of the discriminated union `DropMove | AddMove | SwapMove` on `type`
  - **`PlayersRequest(ScenarioRequest)`**, adding `query`, `limit` (default 50, max 200) and
    `offset`.
  - **Responses**: `LeagueSummary`, `LeagueDetail`, `AnalysisResult` and its parts, `PlayerPage`,
    `PlayerRow`, `Eligibility`, `MoveErrorDetail`, `Warning`, `Freshness`.
- [X] T022 Implement `backend/src/ffmodel/api/app.py`:
  - **`create_app(engine=None)`**: the engine defaults to `get_engine()`.
  - **Startup**: run `migrate(engine)`.
  - **CORS** for `http://localhost:5173`.
  - **Static files**: mount `frontend/dist` at `/` when it exists.
  - **Health**: `GET /api/health` returns `{"status":"ok","schema_version": current_version}`.

  Implement `backend/src/ffmodel/api/routes.py` with:
  - `GET /api/leagues` (`list_leagues` plus the team count)
  - `GET /api/leagues/{league_id}` (teams, managers, freshness; 404 when unknown)

  Routes stay thin: validate, call core or tools, and serialize.
- [X] T023 Add `ffm serve [--host 127.0.0.1] [--port 8000] [--reload]` to
  `backend/src/ffmodel/cli.py`. It runs `uvicorn` on `ffmodel.api.app:create_app` with
  `factory=True`.
- [X] T024 [P] Write `backend/tests/integration/test_api_leagues.py` (FastAPI `TestClient` on
  `impact_engine`):
  - health returns the schema version;
  - the leagues list matches the fixture league;
  - the detail call returns 4 teams with managers and freshness;
  - an unknown league returns 404.

### Frontend shell (needs Node)

- [X] T025 Generate the API types and write the client:
  - Run `npm run gen:api` against `ffm serve` to create `frontend/src/api/schema.d.ts`, and commit
    the generated file.
  - Implement `frontend/src/api/client.ts` with typed functions `listLeagues`, `getLeague`,
    `analyze(req, signal)` and `players(req, signal)`.
  - A non-2xx response throws `ApiError {status, detail}`. A 422 move error carries `move_index`
    and `code`.
- [X] T026 Implement `frontend/src/state/scenario.ts`, a reducer plus a `useScenario()` hook:
  - **State**: `{settings, moves}`.
  - **Actions**: `setLeague`, `setTeam`, `setMode`, `setWindow`, `setOpponent`, `setPeriod`,
    `addMove`, `popMove`, `reset`.
  - **Persistence**: in `sessionStorage` under `ffm.impact.v1`. Reads and writes are wrapped in
    try/catch, so the hook still works when storage is unavailable.
  - **Rules it does not apply**: it never validates moves. The server does that.
- [X] T027 Implement the `frontend/src/App.tsx` layout grid per `contracts/ui.md`:
  - masthead and explainer;
  - the controls row;
  - the record headline;
  - two columns (roster | radar plus table);
  - the breakdown, then footnotes;
  - the right sidebar picker.

  Use placeholder components that later stories fill in. Fetch `analyze` on any state change, with
  an `AbortController` cancelling stale requests and a 250 ms debounce for window and search.
  Previous results stay visible with the `.pending` class while a request is in flight.

**Checkpoint**: the following all pass:
- scoring conformance;
- engine tests;
- projection tests;
- bulk-read tests;
- league API tests.

`ffm serve` answers `/api/health`, and the frontend shell loads with an empty layout.

---

## Phase 3: User Story 1 - See where my team stands in the league (Priority: P1) 🎯 MVP

**Goal**: in strategic mode, show the selected team's record against every team, a radar of
ranks, a rank table, category curves with leader or next-best and league-average overlays, and
the roster with short-history footnotes.

**Independent Test**: `POST /api/impact/analyze` (strategic) on `impact-league` for Alphas
returns a record against 3 teams, a radar with 4 series, a rank for each of the 9 categories, 9
curves with the `selected`, `next_best` and `league_average` roles, and rosters. In the browser,
the page shows all of these for any team picked.

### Tests for User Story 1

- [X] T028 [P] [US1] Write `backend/tests/integration/test_impact_strategic.py` (`impact_engine`,
  `as_of = IMPACT_TODAY`, default seed, 10,000 iterations):
  1. **Alphas**: record units are `matchups`, and wins + losses + ties = 3. Alphas' PTS rank is 1.
  2. **Radar**: 4 series; exactly one has `emphasis` `selected`, and the rest are `other`. The
     ranks are in 1..4.
  3. **Rank table**: one row per format category, in format order.
  4. **Curves**: 9 entries.
     - Alphas, which leads PTS, gets roles {selected, next_best, league_average} for PTS.
     - Deltas gets {selected, leader, league_average}.
  5. **TO**: the team with the lowest projected TO average ranks 1 in TO.
  6. **Reserve slot**: Gamma Hurt (reserve) contributes nothing. Gammas' averages are identical
     whether or not the Gamma Hurt roster row exists.
  7. **Window**: changing the window from 15 to 5 changes the projections.
  8. **Footnotes**: Rookie Ray isn't rostered, so there is no footnote. After the test inserts a
     roster entry giving Rookie Ray to Deltas in place of Delta Three, Deltas' response has the
     footnote "* 2 of 15 games".
  9. **Freshness**: `nba_data_loaded_at` is `2026-11-18T08:00:00+00:00`.
  10. **SC-002**: two identical requests serialize to identical JSON.
  11. **Unsupported format**: a league whose `scoring_format_id` is `points_unknown` gets the
      `UNSUPPORTED_FORMAT` warning, empty projections, and its rosters.
- [X] T029 [P] [US1] Write `backend/tests/integration/test_api_analyze_strategic.py` (`TestClient`):
  - the response matches the `AnalysisResult` schema;
  - `settings` echoes the defaulted `as_of`, `seed` and `iterations`;
  - bad settings return 422: window 0, window 83, iterations 500;
  - an unknown team returns 404.
- [X] T030 [P] [US1] Write `frontend/tests/strategic.test.tsx` (Vitest + RTL, with `client.analyze`
  mocked to a recorded strategic fixture JSON in `frontend/tests/fixtures/strategic.json`, saved
  from T029):
  - The record headline shows "11–5–1" and "vs 17 teams".
  - The radar renders one path per series, with the selected path using `--sel`.
  - The rank table shows 9 rows.
  - 9 curve charts render.
  - The footnote "* 0 of 15 games" appears below the breakdown, and the asterisk appears on the
    roster row.

### Implementation for User Story 1

- [X] T031 [US1] Implement `backend/src/ffmodel/tools/impact_analysis/settings.py`:
  - **`AnalysisSettings`**, a frozen dataclass with the data-model.md defaults:
    - `window=15`, `mode="strategic"`, `as_of = today`
    - `iterations=10_000`, `seed=20261023`, `games_per_period=3`
    - the period defaults to the Mon–Sun week containing `as_of`
  - **`normalize(settings)`**, which resolves the defaults.

  Implement `backend/src/ffmodel/tools/impact_analysis/cache.py`:
  - **`projection_cache`**: an LRU with maxsize 32, keyed by `(league_id, as_of, window, mode,
    period_start, period_end, latest_load_run_id)`.
  - The value is `dict[player_id, PlayerProjection]` for every rostered and free-agent player in
    the league.
- [X] T032 [US1] Implement `backend/src/ffmodel/tools/impact_analysis/analysis.py` with
  `analyze(conn, settings, moves=()) -> AnalysisResult`, a plain dataclass mirroring the API
  shape. Steps:
  1. Load the league snapshot, and build the scenario with `from_snapshot` plus moves. Moves are
     applied in US2; here the list is empty.
  2. Resolve `fmt = get_format(...)`. `UnsupportedFormat` gives the warning and empty projections.
  3. Get projections from the cache via `build_projections`.
  4. For every team, simulate with `strategic_k` over its **active** players only (FR-008).
  5. Compute the selected team's odds against each other team, then the record (unit
     `matchups`).
  6. Compute ranks over all teams, the radar series (selected vs other), and the rank table rows.
  7. Build curves per category with the roles `selected`, and `leader` — or `next_best` when the
     selected team is rank 1 — plus `league_average` (all teams' samples pooled), per research R6.
  8. Build the rosters for every team: player rows with slot, status, NBA team,
     found/requested, a footnote marker, and `moved` (false for now).
  9. Add footnotes for every short-history player in the selected team's roster.
  10. Add freshness and `settings_echo`.
- [X] T033 [US1] Add `POST /api/impact/analyze` to `backend/src/ffmodel/api/routes.py`. It maps
  `ScenarioRequest` → `AnalysisSettings` → `analyze` → `AnalysisResult`, with 404 for an unknown
  league or team.
- [X] T034 [P] [US1] Implement `frontend/src/components/Controls.tsx`:
  - **League and team selects**: populated from `getLeague`. Options show "Team — Manager".
  - **Mode toggle** (Strategic | Tactical): an active pill uses the yellow `--yours` background.
  - **Window**: a number input, 1–82.

  Also add `RecordHeadline.tsx` (team, manager, record, units label) and `DataLine.tsx`
  (freshness).
- [X] T035 [P] [US1] Implement `frontend/src/components/Radar.tsx` with D3 (`d3-scale`
  `scaleLinear` for radius, `d3-shape` `lineRadial` with `curveLinearClosed`):
  - one axis per category, labeled with the category label;
  - rank 1 at the rim and rank N at the center;
  - the selected series is drawn last with `--sel` at full opacity;
  - other series use `--other` at 35% opacity, and the opponent uses `--opp`;
  - no gridlines beyond faint axis spokes.
- [X] T036 [P] [US1] Implement `frontend/src/components/CategoryTable.tsx`.
  - **Strategic**: a "CATEGORY / RANK" table.
  - **Tactical** (filled in by US3): differences.
  - Ratio values show 3 decimals without a leading zero (`.473`).
  - Column headers are small, ALL CAPS, weight 900, color `--muted`.
- [X] T037 [P] [US1] Implement `frontend/src/components/CategoryCurves.tsx` with Observable Plot:
  - a 3 × 3 grid of small charts, one per category;
  - each is `Plot.areaY` for the selected series in `--sel` at 30% opacity plus `Plot.lineY`
    outlines;
  - the overlays (`--leader`, `--avg`, `--opp`) are lines at reduced opacity;
  - minimal axes, with no y-axis ticks;
  - a legend naming each role and team.

  Render the charts into refs and clean them up on unmount.
- [X] T038 [P] [US1] Implement `frontend/src/components/Roster.tsx` as display only. "−" is added
  in US2. Each row shows: name, NBA team, positions, slot, and status (muted gray for reserve
  rows), plus the footnote asterisk.

  Implement `frontend/src/components/Footnotes.tsx` to list the `footnotes`.
- [X] T039 [US1] Wire US1's components into `frontend/src/App.tsx`, and save the recorded fixture
  `frontend/tests/fixtures/strategic.json` from a real `analyze` response (from T029's
  `TestClient` output).

**Checkpoint**: US1 is fully usable read-only. Pick any team and read its strategic standing.

---

## Phase 4: User Story 2 - Try roster moves and see the impact (Priority: P1)

**Goal**: drop, add a free agent, swap with another team (giving a roster player or a free
agent), and reset. The picker shows eligibility from the server, and results update after every
move.

**Independent Test**: on `impact-league`, as Gammas:
1. Drop Gamma One; it then appears as a free agent.
2. Add Busy Streamer.
3. Swap for Alpha One, giving Gamma Two (a trade).
4. Reset; the rosters equal the base.
5. Confirm the DB is unchanged.

### Tests for User Story 2

- [ ] T040 [P] [US2] Write `backend/tests/unit/test_scenario_moves.py` (a synthetic scenario with
  capacity 3) for every transition and error code in data-model.md:
  - `Drop`: the player becomes a free agent. Dropping a reserve player doesn't increase
    `open_active_slots`.
  - `Add`: a free agent goes to an active slot. On a full team → `NO_ACTIVE_SLOT`. A non-free-agent
    → `NOT_FREE_AGENT`.
  - Swap with a roster player: P and Q exchange teams, both in active slots. No open slot is
    needed. A reserve-slot Q is allowed and becomes active on T.
  - Swap with a free agent: the free agent goes to T as active, and P comes to the selected team.
    No open slot → `NO_ACTIVE_SLOT`.
  - Acquiring your own player → `SAME_TEAM`. Unknown IDs → `UNKNOWN_PLAYER`. Dropping someone not
    on the team → `NOT_ON_TEAM`.
  - `check_invariants` holds after every valid move, no move ever creates a reserve slot, and the
    base scenario is never mutated (frozen).
- [ ] T041 [P] [US2] Write `backend/tests/integration/test_impact_moves.py` (`impact_engine`):
  1. Dropping Gamma One changes Gammas' projections, and the picker (T045) lists Gamma One as a
     free agent.
  2. Adding Busy Streamer to Gammas fills the open slot. The response shows `open_active_slots =
     0`, and the row has `moved = true`.
  3. Swapping for Alpha One, giving Gamma Two, updates both rosters in the response.
  4. **Common random numbers**: after the drop, Betas' and Deltas' category samples equal their
     pre-move samples exactly.
  5. An invalid move at index 1 raises `MoveError(move_index=1, code="NO_ACTIVE_SLOT")`.
  6. **SC-009**: after 20 analyze calls with moves, a checksum of every table equals the
     pre-test checksum.
  7. Reset (an empty move list) gives a result identical to the first base call.
- [ ] T042 [P] [US2] Write `backend/tests/integration/test_api_moves_players.py` (`TestClient`):
  - **Move errors**: `analyze` with an invalid move returns 422 with `{move_index, code,
    message}`.
  - **`players` as Gammas** (1 open slot):
    - free agents have `can_add = true`;
    - Alpha One has `can_add = false`, a reason, and `swap_give_options = ["roster",
      "free_agent"]`;
    - the list is ordered free agents first, then by name.
  - **`players` as Alphas** (full): free agents have `can_add = false` with the reason "No open
    active slot". Rostered players offer `["roster"]` only.
  - **Search**: `query="streamer"` returns the 2 streamers, and `query="busy strea"` returns 1.
    Paging works through `limit` and `offset`.
- [ ] T043 [P] [US2] Write `frontend/tests/moves.test.tsx` (mocked client):
  - pressing "−" dispatches a drop move and re-requests;
  - "+" is disabled with its title set from `add_blocked_reason`;
  - "+" on a rostered player opens `SwapDialog` showing only the allowed give options;
  - a 422 response shows the message inline and the move isn't kept;
  - Reset clears moves and is disabled when there are none;
  - moves survive re-mounting through `sessionStorage`.

### Implementation for User Story 2

- [ ] T044 [US2] Add the move transitions to `backend/src/ffmodel/core/scenario/scenario.py`:
  - frozen dataclasses `Drop(player_id)`, `Add(player_id)`, `Swap(acquire_id, give_id)`;
  - `apply(scenario, selected_team_id, move) -> Scenario`;
  - `apply_all(scenario, team_id, moves)`, which raises `MoveError(move_index, code, message)` on
    the first invalid move.

  The semantics and codes are exactly as in data-model.md and research R7.
- [ ] T045 [US2] Implement `backend/src/ffmodel/tools/impact_analysis/picker.py` with
  `list_players(conn, settings, moves, *, query, limit, offset) -> PlayerPage`:
  - **Which players**: every active NBA player, plus every rostered player (inactive or
    otherwise), not on the selected team in the scenario.
  - **Search**: by `name_words` and `search_name`, as in 001 `search_players`, applied in memory
    over the scenario's pool.
  - **Owner**: the team name, or "FA".
  - **Eligibility**, computed from `Scenario` only:
    - `can_add` means a free agent while the selected team has an open slot;
    - `swap_give_options`: `"roster"` when the selected team has any players, and `"free_agent"`
      when it has an open active slot;
    - `add_blocked_reason` says why "+" is disabled.
  - **Order**: free agents first, then by name. Then page the result.
- [ ] T046 [US2] Extend `analysis.py`:
  - apply the moves with `apply_all`;
  - mark `moved = true` on players whose team differs from the base;
  - add `open_active_slots` per roster.

  Add `POST /api/impact/players` to `routes.py`, and map `MoveError` to a 422 with the
  `MoveErrorDetail` body in both endpoints.
- [ ] T047 [P] [US2] Implement `frontend/src/components/PlayerPicker.tsx`:
  - a search input, debounced by 250 ms;
  - a paged list of 50 rows;
  - each row: "+", name, NBA team, owner, status, asterisk;
  - "+" is disabled when `!can_add && swap_give_options.length === 0`, with
    `title = add_blocked_reason`;
  - "+" calls `addMove({type:"add"})` for a free agent, or opens the swap dialog for a rostered
    player.

  Hovering a row shows `--hover`.
- [ ] T048 [P] [US2] Implement `frontend/src/components/SwapDialog.tsx`:
  - a heading "Give <team> one of:";
  - a list of the selected team's roster, when `"roster"` is allowed;
  - a free-agent search using the `players` endpoint filtered to FA, when `"free_agent"` is
    allowed;
  - confirm appends `{type:"swap", acquire_id, give_id}`;
  - Esc or Cancel closes it.
- [ ] T049 [US2] Update `frontend/src/components/Roster.tsx`:
  - add "−" (destructive style) on every row, dispatching a drop;
  - rows with `moved` get the `--yours` background;
  - show "N open slot(s)".

  Wire Reset in `Controls.tsx`, disabled when there are no moves. Handle `ApiError` 422 by
  popping the last move and showing the message inline near the control that caused it.

**Checkpoint**: US1 and US2 work together. Every move updates the strategic view, and Reset
restores the base.

---

## Phase 5: User Story 3 - Win this week's matchup (Priority: P2)

**Goal**: tactical mode with an opponent and a period. Games remaining scale contributions, the
record counts categories, and the page shows the matchup win %, a differences table, and
opponent-only overlays.

**Independent Test**: as Gammas against Betas in tactical mode for 11-16 → 11-22, with
`as_of = 11-18`:
- adding Busy Streamer (4 games, s 0.9) projects better than adding Steady Streamer (1 game,
  s 1.0);
- in strategic mode the order is reversed (SC-004).

### Tests for User Story 3

- [ ] T050 [P] [US3] Write `backend/tests/unit/test_engine_modes.py` (synthetic projections, no
  DB) for **SC-004**:
  - player A has μ = 0.9·base and 2 games remaining; player B has μ = 1.0·base and 1 game
    remaining; both have availability 1.0;
  - in tactical mode, the team with A has a higher matchup win probability than the team with B
    against the same opponent;
  - in strategic mode, the team with B is higher.

  Repeat over 5 seeds and assert the result holds every time (100%).
- [ ] T051 [P] [US3] Write `backend/tests/integration/test_impact_tactical.py` (`impact_engine`,
  `as_of = IMPACT_TODAY`):
  1. Gammas vs Betas in tactical mode with the default period (11-16…11-22):
     - the record unit is `categories`, and W + L + T = 9;
     - `matchup_win_probability` is in [0, 1];
     - the category table kind is `differences`, with `favors` consistent with the sign of each
       difference and the direction (for TO, lower favors).
  2. The radar has exactly 2 series (selected and opponent). The curves' roles are {selected,
     opponent}.
  3. Roster rows show `games_remaining`: Busy Streamer 4, Steady Streamer 1, Gamma One (CHI) 3.
     The postponed MIA–NYK game is not counted.
  4. **SC-004 on the DB**: Gammas plus Busy Streamer gets a higher matchup win probability
     against Betas than Gammas plus Steady Streamer in tactical mode. In strategic mode, Steady
     beats Busy on Gammas' expected matchup wins.
  5. No opponent gives `OPPONENT_REQUIRED`, rosters only, and no 500 error.
  6. A period of 11-23…11-23 (no games) gives `NO_GAMES_REMAINING`.
  7. **Constitution IV**: the same roster gives different category averages in the two modes.
- [ ] T052 [P] [US3] Write `frontend/tests/tactical.test.tsx` (mocked client with
  `frontend/tests/fixtures/tactical.json`):
  - the opponent and period controls appear only in tactical mode;
  - the headline shows "5–3–1 categories vs Betas" and "62% to win";
  - the differences table shows the signs and favors markers;
  - the roster and picker show games remaining;
  - `OPPONENT_REQUIRED` shows "Choose an opponent".

### Implementation for User Story 3

- [ ] T053 [US3] Extend `backend/src/ffmodel/tools/impact_analysis/analysis.py` for
  `mode="tactical"`:
  - **Inputs**: projections with `games_remaining` for [`as_of`, `period_end`], using
    `tactical_k`.
  - **Simulation**: simulate every team, since ranks are among all teams, but compute odds only
    for selected vs opponent.
  - **Results**:
    - the record has unit `categories`, plus `matchup_win_probability`;
    - the category table holds differences, with `favors` computed via
      `fmt.compare`-consistent direction;
    - the radar has 2 series;
    - curves have the roles {selected, opponent}.
  - **Warnings**:
    - `OPPONENT_REQUIRED` when there is no opponent: skip the simulation and return rosters only;
    - `NO_GAMES_REMAINING` when every k is 0.
  - **Rosters**: fill `games_remaining` on the roster rows.
- [ ] T054 [US3] Extend `picker.py` to fill `games_remaining` in tactical mode, using
  `count_team_games_bulk` for the page's players.
- [ ] T055 [P] [US3] Update the frontend:
  - **`Controls.tsx`**: an opponent select (the other teams) and period start/end date inputs,
    shown only in tactical mode, defaulting from `settings_echo`.
  - **`RecordHeadline.tsx`**: the tactical units label and win %.
  - **`CategoryTable.tsx`**: the differences view, with selected average, opponent average, and a
    difference whose favors marker is bold and colored with `--sel` or `--opp`.
  - **`Roster.tsx` and `PlayerPicker.tsx`**: a games-remaining column in tactical mode.
- [ ] T056 [US3] Save `frontend/tests/fixtures/tactical.json` from a real tactical response
  (T051).

**Checkpoint**: all three stories work. Tactical streaming decisions differ from strategic ones,
as the docs intend.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T057 [P] Write `backend/tests/slow/test_real_league.py`, marked `@pytest.mark.slow`, against
  the real DB (`FFMODEL_DB_URL`, league `ccsv-2026`):
  - **SC-001**: for 3 teams in each mode (tactical uses each team's first other team as the
    opponent), `analyze` with a warm projection cache takes under 2.0 s. Also one cold call under
    2.0 s.
  - **SC-003**: for **every** team in both modes, run 5 seeds (1–5) at default iterations. The
    maximum spread of every matchup and category `p_win` stays at or under 0.03. Record the
    observed maximum in the test output.
- [ ] T058 [P] Write `backend/tests/integration/test_layering_002.py`, or extend the existing
  layering test, asserting that `lint-imports` passes with the new contracts. Also add a test that
  `ffmodel.core.sim` and `ffmodel.core.scoring` import without SQLAlchemy usage at import time.
- [ ] T059 [P] Update `backend/README.md` with:
  - `ffm serve`;
  - the API overview, linking `specs/002-impact-analysis/contracts/api.md`;
  - the frontend dev loop (`npm run dev`, `npm run gen:api`);
  - the `slow` test marker.

  Create `frontend/README.md` with setup, scripts, and the Node 22 prerequisite.
- [ ] T060 Run `uv run ruff check src tests && uv run ruff format`, `uv run lint-imports`, and
  `uv run pytest` in `backend/`, plus `npm run build && npm test` in `frontend/`. Fix all
  findings.
- [ ] T061 Run quickstart sections B, C and D manually: the real league, the browser
  walk-through steps 1–7, and the built bundle served by `ffm serve`. Append a "Validation log" to
  `specs/002-impact-analysis/quickstart.md` with:
  - the timings and the SC-003 observed maximum spread;
  - any style deviations found;
  - screenshots described in text.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**:
  - T001 → T002 and T003.
  - T004 needs Node 22 (user approval to install).
  - T005 needs T004.
- **Foundational (Phase 2)** blocks every story.
  - Scoring: T006 → T007 → T008.
  - Bulk reads: T009 → T010.
  - Projections: T011 (needs T007 and T009) → T012 and T013.
  - Engine: T014 (needs T007 and T011) → T016. T015 → T017.
  - Scenario and fixture: T018. T019 → T020.
  - API: T021 → T022 → T023 and T024.
  - Frontend shell: T025 (needs T022 and T004) → T026 → T027.
- **US1 (Phase 3)** needs all of Phase 2.
- **US2 (Phase 4)** needs Phase 2. Its frontend tasks (T047–T049) build on US1's `Roster` and
  `Controls`, and its backend tasks extend US1's `analysis.py` (T032). The backend part of US2
  (T040, T044, T045) can start in parallel with US1.
- **US3 (Phase 5)** needs Phase 2 and extends `analysis.py` (after T032) and `picker.py` (after
  T045).
- **Polish (Phase 6)** needs the stories you intend to ship.

### Shared files (edit in order, never in parallel)

- `analysis.py`: T032 → T046 → T053
- `routes.py`: T022 → T033 → T046
- `Roster.tsx`: T038 → T049 → T055
- `Controls.tsx`: T034 → T049 → T055
- `CategoryTable.tsx`: T036 → T055
- `cli.py`: T023 only

### Within Each Story

Tests first (they must fail), then core and tool code, then the API, then the frontend, then
wiring.

## Parallel Examples

```bash
# Phase 2, after T007 and T009:
Task: "T008 scoring conformance"   Task: "T010 bulk read tests"   Task: "T012 projection unit tests"
Task: "T015 curves.py"             Task: "T018 scenario base"     Task: "T019 impact fixture"

# US1 tests together:
Task: "T028 strategic tool test"   Task: "T029 analyze API test"   Task: "T030 strategic.test.tsx"
# US1 frontend components together (after T027):
Task: "T034 Controls"  Task: "T035 Radar"  Task: "T036 CategoryTable"  Task: "T037 CategoryCurves"  Task: "T038 Roster"

# US2 backend can overlap US1 frontend:
Task: "T040 scenario move tests"   Task: "T044 move transitions"   Task: "T045 picker.py"
```

## Implementation Strategy

### MVP (US1)

1. Phases 1–2. **Node must be installed for T004, T025–T027.** The backend parts of Phase 2 can
   proceed without it.
2. Phase 3 (US1): a read-only strategic standing.
3. **Stop and validate**: run quickstart steps C.1 and C.7 (style).

### Incremental

1. **US2**: moves and the picker. This makes it a decision tool; the spec's purpose is met.
2. **US3**: tactical streaming.
3. **Polish**: the real-league SC-001 and SC-003 checks, the READMEs, and the validation log.

### Backend-first option, if Node approval is pending

Do every backend task (T001–T003, T006–T024, T028–T029, T031–T033, T040–T042, T044–T046,
T050–T051, T053–T054, T057–T058). The API is then complete and testable through
`curl`/`TestClient`. Then do the frontend tasks in one pass.
