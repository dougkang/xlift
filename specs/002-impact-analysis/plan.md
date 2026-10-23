# Implementation Plan: Impact Analysis Tool

**Branch**: `002-impact-analysis` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-impact-analysis/spec.md`

## Summary

This feature builds the first tool on the 001 data contract: a web page that shows how adding,
dropping or swapping players changes a fantasy team, both against the whole league (strategic)
and against this week's opponent (tactical). The pieces:

- **Scoring formats**: a pluggable scoring-format layer, with 9cat h2h as the first format.
- **Player model**: each player's per-game stats are fitted jointly as a multivariate normal, with
  covariance shrinkage for short histories.
- **Simulation**: a vectorized Monte Carlo engine, 10,000 iterations by default, with each player's
  random stream seeded by player ID so before/after comparisons aren't noise.
- **Scenarios**: immutable scenario transitions for moves.
- **API**: a stateless FastAPI service.
- **Frontend**: React + TypeScript + Vite, with a D3 radar and Observable Plot category curves.

A prototype on the real 18-team league ran 10,000 strategic simulations in 0.15 s, and the win
probabilities moved at most 2.0 points across 5 seeds (SC-001 and SC-003 look achievable).

## Technical Context

**Language/Version**: Python ≥3.12 (the uv venv currently resolves to 3.14). TypeScript 5.x on
Node 22 LTS.

**Primary Dependencies**:
- **Backend**: NumPy 2.x, FastAPI 0.16x, uvicorn, and Pydantic 2. Plus the 001 stack: SQLAlchemy
  Core, Typer.
- **Frontend**: React 19, Vite, D3 (scale and shape), and `@observablehq/plot`.
- **Dev**: `openapi-typescript`, Vitest, React Testing Library, `httpx`.

**Storage**: SQLite through the 001 data contract. Read-only; this feature has no schema change.

**Testing**: pytest, with three groups:
- unit and integration tests on synthetic projections and the fixture DB;
- an API contract suite;
- a `slow` marker for real-DB timing and stability.

Plus Vitest with a mocked API, and the import-linter layering contracts.

**Target Platform**: A local workstation, with the browser at `localhost` and one user.

**Project Type**: A web application: `backend/` (Python API plus core) and `frontend/` (SPA).

**Performance Goals**:
- results update in under 2 s after any change (SC-001); the measured simulation core takes
  0.15 s;
- the picker search answers in under 300 ms.

**Constraints**:
- deterministic for a given seed (SC-002);
- seed spread of at most 3 points (SC-003);
- no domain logic in the frontend;
- moves never written to the DB.

**Scale/Scope**: one league of 18 teams with about 10 active players each; about 550 pickable
players; 9 categories; 10,000 iterations.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | How this plan complies |
|---|---|---|
| I. Statistically Faithful Aggregation | ✅ | Ratios are Σ makes / Σ attempts per simulation; ranks use the ratio of means; TO is reversed through `higher_is_better`; NaN on zero attempts counts as a tie; ties are counted and reported. Validity rules apply to team totals, which avoids the measured 8.6% per-player clipping bias (research R2). |
| II. Pluggable Scoring Formats | ✅ | `core/scoring` interface plus registry. The engine, tool and API never name a category. A conformance suite runs over every registered format (contracts/scoring-format.md). |
| III. Distribution-Based Modeling | ✅ | A multivariate normal per player over a user-chosen window (1–82). Seed and iteration count are settable. Fit error (n, standard error) is kept on each projection for later propagation. |
| IV. Tactical vs. Strategic | ✅ | The mode changes the computation: k = scheduled games (tactical) vs. k ~ Binomial(3, availability) (strategic). The mode logic lives in core and the tool. A dedicated test covers the streaming example (SC-004). |
| V. Visualization | ✅ | contracts/ui.md, with colors and typography from `docs/style.md` (research R9). The frontend draws only server-computed series. |
| VI. Data Source Orthogonality | ✅ | All reads go through `core.data` (001 functions plus 3 new bulk reads), which is SQL against the contract. Nothing imports adapters. |
| VII. Modular Core | ✅ | Layering is `core → tools/impact_analysis → api → frontend`, with new import-linter contracts. Scenario moves are pure transitions; Reset is an empty move list; nothing is written to the DB. |
| Tech stack | ✅ | Python, FastAPI with a thin routes layer, Pydantic as the contract with TypeScript generated from OpenAPI, React + TS + Vite, Plot and D3 only, SQLite. |
| Quality gates | ✅ | Tests are planned for every gate: ratio aggregation, lower-is-better, outcomes with ties, fixed-seed determinism, distinct tactical and strategic computations, and format conformance. |

**Post-design re-check**: still passing.
- **Spec change**: the spec's "correlations aren't modeled" assumption was replaced by joint
  modeling (research R1). It strengthens Principle I and doesn't deviate from any principle.
- **Frontend eligibility**: the API supplies `can_add`, `swap_give_options` and
  `open_active_slots`, so the frontend applies no roster rules (stack rule).

## Project Structure

### Documentation (this feature)

```text
specs/002-impact-analysis/
├── plan.md
├── research.md          # R1 model · R2 simulation · R3 scoring · R4 availability · R5 tactical · R6 display · R7 moves · R8 API · R9 frontend · R10 layering
├── data-model.md        # in-memory types; no schema change; 3 new core reads
├── quickstart.md
├── contracts/
│   ├── scoring-format.md
│   ├── api.md
│   └── ui.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                         # + numpy, fastapi, uvicorn[standard]; dev + httpx; markers + slow
├── .importlinter                          # + core ↛ tools/api, tools ↛ api, adapters ↛ tools/api
├── src/ffmodel/
│   ├── core/
│   │   ├── data/                          # 001 + bulk.py (last-N bulk, team-games bulk, freshness)
│   │   ├── scoring/                       # base.py (Category, ScoringFormat, registry), nine_cat.py
│   │   ├── model/                         # projection.py (fit, shrinkage, availability, games remaining)
│   │   ├── sim/                           # engine.py (team samples, category values, odds, ranks), curves.py (KDE)
│   │   └── scenario/                      # scenario.py (Scenario, moves, MoveError)
│   ├── tools/
│   │   └── impact_analysis/               # settings.py, analysis.py (→ AnalysisResult), picker.py, cache.py
│   ├── api/                               # app.py (FastAPI factory, static serving), schemas.py (Pydantic), routes.py
│   └── cli.py                             # + `ffm serve`
└── tests/
    ├── scoring/                           # conformance suite
    ├── unit/                              # projection fit, scenario moves, engine (synthetic projections)
    ├── integration/                       # bulk reads, tool on fixture DB (new impact fixture builder), API contract
    └── slow/                              # real-DB SC-001 / SC-003 (marker: slow)

frontend/
├── package.json, vite.config.ts (proxy /api → :8000), tsconfig.json, index.html
├── src/
│   ├── api/                               # schema.d.ts (generated), client.ts
│   ├── state/                             # scenario.ts (settings + moves, sessionStorage)
│   ├── components/                        # Controls, RecordHeadline, Roster, Radar (D3), CategoryTable,
│   │                                      # CategoryCurves (Plot), PlayerPicker, SwapDialog, Footnotes
│   ├── styles/                            # tokens.css (style.md), base.css
│   └── App.tsx, main.tsx
└── tests/                                 # Vitest + RTL with mocked API
```

**Structure Decision**: this is the web-application layout the 001 plan anticipated (`backend/`
plus a sibling `frontend/`).
- **The tool package**: the tool lives in `ffmodel.tools.impact_analysis`, so a future Player
  Comparison tool can sit beside it and reuse `core`.
- **Test data**: tool tests use a new fixture builder (`tests/fixtures/impact_dataset.py`) layered
  on the 001 schema. The 001 `dataset.py` is left alone, because 001's tests assert exact counts
  from it.

## Complexity Tracking

| Deviation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Multivariate normal with covariance shrinkage, beyond the spec's original "independent normals" assumption | FG% and FT% need makes and attempts to move together (Principle I). Shrinkage keeps short histories well-defined | Independent normals misrank the ratio categories; bootstrap isn't a fitted distribution (Principle III) |
| Process-level projection cache | Keeps a move-only re-analysis under SC-001's 2 s without refitting about 180 players | Refitting on every request works (about 0.1 s) but wastes most of the budget once the picker is added. The cache key includes the latest `load_run` ID, so it can't serve stale data |
