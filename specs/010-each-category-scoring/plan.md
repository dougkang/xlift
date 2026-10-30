# Implementation Plan: H2H Each-Category Scoring

**Branch**: `010-each-category-scoring` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-each-category-scoring/spec.md`

## Summary

The league scores H2H Each Category: every category of a matchup is a W, L or T in the
standings. The model is unchanged; what changes is the record the app reports.

- **Core**: `ScoringFormat.standings` (`"matchup"` default, `"category"`), a second registered
  format `9cat_h2h_each`, and `expected_record()` summing per-category odds (research R1, R2).
- **Tool**: Impact Analysis's strategic headline, H2H rows and totals, tactical headline and the
  change builder branch on `fmt.standings` (R3–R5). Most-categories output is unchanged (R7).
- **API**: additive fields (`standings`, `expected_record`, `expected`, `expected_wins`,
  `win_pct`), some existing ones nullable (contracts/api.md).
- **Frontend**: `RecordHeadline`, `RecordTable` and the `headline` / `h2h` help branch on
  `result.standings` (R8).
- **CLI**: `--format` validated against the registered formats (R6).
- **Docs**: overview and Tool 1 describe both rules (R9).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/React 19 (frontend)

**Primary Dependencies**: NumPy, FastAPI/Pydantic, SQLAlchemy, React + Vite. No new dependencies.

**Storage**: SQLite, no schema change

**Testing**: pytest (unit, fixture integration, scoring conformance, snapshot), import-linter,
Vitest/Testing Library

**Target Platform**: local web app (`ffm serve`)

**Project Type**: web application (backend + frontend)

**Performance Goals**: no added simulation; the expected record reuses computed odds.

**Constraints**: most-categories results identical to pre-010 (SC-004); the frontend does no
arithmetic beyond formatting; help names no files.

**Scale/Scope**: 18 teams, 9 categories, 17 opponents.

## Constitution Check

| Principle | Status | Note |
|---|---|---|
| I. Faithful aggregation | ✅ | No aggregation change. Ties: an explicit rule, T reported and counted ½ in win %. Direction via `fmt.compare`. |
| II. Pluggable formats | ✅ | The standings rule is declared by the format; tools read `fmt.standings`, never an id. The new format is a registration in the format module and runs the conformance suite. |
| III. Simulation-driven | ✅ | Expected record = mean of simulated per-category outcomes; seeded, deterministic. |
| IV. Tactical vs strategic | ✅ | Tactical: the current matchup's expected category record; strategic: summed over every other team. Both computed in the tool/core, tested in both modes. |
| V. Visualization | ✅ | Same headline and table idioms; no new colors or fonts. |
| VI. Data orthogonality | ✅ | No schema change; the adapter doesn't import scoring (validation in the CLI). |
| VII. Modular core | ✅ | `expected_record` and the rule live in core; the API stays thin; the frontend renders API numbers. |
| Workflow gates | ✅ | Tests for both rules with ties in both modes; conformance for both formats; docs updated in the same change. |

**Post-design re-check**: passing, no deviations.

## Project Structure

### Documentation (this feature)

```text
specs/010-each-category-scoring/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/src/ffmodel/
├── core/scoring/base.py, nine_cat.py      # standings field, 9cat_h2h_each
├── core/sim/engine.py, __init__.py        # ExpectedRecord, expected_record
├── tools/impact_analysis/analysis.py      # headline, H2H rows, totals by rule
├── tools/impact_analysis/changes.py       # expected-wins and win % changes
├── api/schemas.py                         # additive models
└── cli.py                                 # --format validation
backend/tests/                             # unit, integration, conformance, pre010 snapshot
frontend/src/
├── components/RecordHeadline.tsx, RecordTable.tsx
├── help/content.ts, format.ts, App.tsx
└── api/schema.d.ts                        # regenerated
frontend/tests/                            # each-category fixtures and tests
docs/overview.md, docs/tool1-impact-analysis.md
```

**Structure Decision**: the existing web-app layout; no new modules.

## Complexity Tracking

None.
