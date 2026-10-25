# Implementation Plan: Recency-Weighted Player Projections

**Branch**: `006-recency-weighted-projections` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-recency-weighted-projections/spec.md`

## Summary

Replace the equal-weight 15-game fit with a **recency-weighted** fit over up to *X* games
(default 82). Game *j* games ago weighs 0.5^(*j*/40) × 0.25^(season age). The weighted mean and
covariance replace the plain ones, and the **effective number of games** (Σ*w*)²/Σ*w*² replaces
the game count wherever a sample size is used. Keep and document the **mean shrinkage** toward a
typical player that was added after 005. Its exemption for blocks becomes a property of the
scoring format, as Principle II requires. **Availability is unchanged**: it's still computed over
the most recent 15 games, whatever the lookback.

All changes are in the core model (`core/model`), the scoring-format interface, the default
settings, one help string, and the docs. The simulation, the API's shape, and the data schema
don't change. A reproducible backtest script under `analysis/` measures the success criteria.

**Implementation status**: a pre-spec draft of most of this exists in the working tree
(uncommitted). It includes the mean shrinkage from earlier work, which passes its tests, and a
draft of the weighted fit with two expected footnote-test failures. `tasks.md` reconciles the
draft with this plan. In particular, the draft's hard-coded `UNSHRUNK_STATS = ("blk",)` moves into
the format module (research R4).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript (frontend help text only)

**Primary Dependencies**: NumPy (fit), FastAPI/Pydantic (unchanged contract shape), SQLAlchemy
(reads); the analysis backtest uses polars and the `analysis/` project's modules

**Storage**: SQLite. No schema change (reads `player_game`, `game`, `player_team_stint` as
today)

**Testing**: pytest (unit DB-free and fixture integration), `ruff`, `lint-imports`; Vitest for
the frontend; the backtest script for SC-001–003 and SC-007

**Target Platform**: local web app (`ffm serve`) on macOS

**Project Type**: web application (backend + frontend)

**Performance Goals**: a cold analysis of the real league stays within 1.5× today's time (about
0.9 s today)

**Constraints**: deterministic results for the same inputs and seed. The core stays importable
and testable without a database (Constitution VII)

**Scale/Scope**: about 600 players in the prior pool × up to 82 games; 18 teams × 10 actives per
analysis

## Constitution Check

*GATE: must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | Ratios stay makes ÷ attempts at team level. Percentage shrinkage rebuilds per-game makes from a shrunk rate × shrunk attempts, so team FG% and FT% remain combined makes ÷ attempts. Directions and ties are untouched. |
| II. Pluggable formats | ✅ (after fix) | The draft hard-codes `"blk"` in core. Research R4 moves the exemption to a `ScoringFormat.unshrunk_stats` field, set by the 9cat module. Ratio pairs and caps already come from the format. |
| III. Simulation-driven | ✅ | It's still a joint normal per player, simulated by Monte Carlo. The window stays user-specifiable (now a maximum lookback). Fit error stays represented (standard error over effective games). This is the "decayed past-season weighting" the principle anticipates. |
| IV. Tactical vs strategic | ✅ | Both modes consume the same projections. Availability, which strategic mode uses, is unchanged. Tactical games-remaining logic is untouched. |
| V. Visualization | ✅ | Only a help string changes. There are no new visuals, colors or idioms. |
| VI. Data source orthogonality | ✅ | No schema or adapter change. Reads go through `core.data`. |
| VII. Modular core | ✅ | The weighting and shrinkage live in `core.model` (DB-free `fit.py`). The tool cache only calls core. The API stays thin. The backtest lives in `analysis/`, outside the app layers. |
| Workflow gates | ✅ | Core tests cover the weighted fit (and that it reduces to the unweighted fit), effective games, season age, shrinkage, the exemption, and determinism. `docs/` and research notes are updated in the same change. |

**Post-design re-check**: passing. The only design-level change from the draft is R4 (the
exemption in the format), which resolves the Principle II issue.

## Project Structure

### Documentation (this feature)

```text
specs/006-recency-weighted-projections/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R9
├── data-model.md        # Phase 1: changed model entities and settings
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── api.md           # Window default and meaning (shape unchanged)
│   ├── scoring-format.md# New ScoringFormat.unshrunk_stats field
│   └── ui.md            # Help text, default, footnote
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/src/ffmodel/
├── core/model/fit.py            # weighted fit, effective games, MeanPrior.exempt, shrink uses n_eff
├── core/model/projection.py     # build_prior/build_projections: weights, exemption from format,
│                                # availability over the most recent 15 games
├── core/model/__init__.py       # exports (build_prior, MeanPrior, RatioPrior, …)
├── core/scoring/base.py         # ScoringFormat.unshrunk_stats (new, default ())
├── core/scoring/nine_cat.py     # unshrunk_stats=("blk",)
├── core/data/bulk.py            # get_players_with_games (prior pool; from earlier draft)
├── tools/impact_analysis/cache.py     # one prior per settings key (from earlier draft)
├── tools/impact_analysis/settings.py  # DEFAULT_WINDOW = 82
└── api/schemas.py               # ScenarioRequest.window default 82

backend/tests/
├── unit/test_projection.py          # weighted fit, n_eff, season age, shrinkage, exemption
├── unit/ (scoring conformance)      # unshrunk_stats ⊆ base_stats
├── integration/test_projection_db.py# availability unchanged at window 82; prior wiring
├── integration/test_impact_*.py     # footnote expectations at the new default
└── contract/test_offline_reads.py   # get_players_with_games registered

frontend/src/
├── state/scenario.ts            # default window 82
└── help/content.ts              # "Last X games" help (FR-015)

analysis/
└── projection_backtest.py       # reproducible backtest for SC-001–003, SC-007

docs/tool1-impact-analysis.md     # domain rule: weighting, shrinkage, blocks exemption
specs/002-impact-analysis/research.md  # R1 addendum (model notes)
```

**Structure Decision**: this is the existing web-application layout. The changes are confined to
the core model, the format interface, the defaults, and docs, plus one analysis script.

## Complexity Tracking

No constitution violations to justify. The draft's Principle II issue is resolved by design
(research R4).
