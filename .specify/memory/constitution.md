# FF-Model Constitution

## Core Principles

### I. Statistically Faithful Aggregation (NON-NEGOTIABLE)

Team-level numbers MUST be computed in a way that respects how each category is scored.

- Every category MUST declare its aggregation kind: additive (summed across players and games),
  ratio (numerator and denominator aggregated separately, ratio computed only at team level), or
  another kind explicitly defined by the scoring format.
- Ratio stats (e.g. FG%, FT%) MUST NOT be averaged or summed as percentages.
- Every category MUST declare its direction (higher-is-better or lower-is-better, e.g. TO), and
  that direction MUST be honored in every comparison, ranking, outcome computation, and chart axis.
- Ties MUST be handled by an explicit rule and reported, never silently dropped.

Rationale: These are the documented gotchas of category scoring. A wrong aggregation produces
confidently wrong advice, which is worse than no advice.

### II. Pluggable Scoring Formats

The scoring format MUST be interchangeable without changes to the engine or the tools.

- A scoring format is a self-contained module that defines: its categories (with aggregation kind
  and direction), how raw player stats map to category values, and how team totals turn into
  outcomes (category wins, matchup result, points, ranks, etc.).
- The data layer, simulation engine, and tools MUST depend only on the scoring-format interface,
  never on a concrete format. Hard-coding category names, counts, or win rules outside a format
  module is a violation.
- 9 category head-to-head (9cat h2h) is the first and default implementation. Adding a format
  (e.g. 8cat, points, roto) MUST require only a new format module and its tests.
- Each format MUST ship with a conformance test suite run against the shared interface contract.

Rationale: Leagues differ; the statistical engine is the reusable asset, the format is a
configuration of it.

### III. Distribution-Based, Simulation-Driven Modeling

Player projections MUST be modeled as probability distributions, not point estimates.

- Each player's per-stat contribution MUST be fit to a distribution (normal by default) over a
  configurable window of past games (the "X games" window MUST be user-specifiable).
- Team and matchup outcomes MUST be derived by Monte Carlo simulation over those distributions,
  then scored by the active scoring format.
- Simulations MUST be reproducible: the random seed and iteration count MUST be controllable so
  that identical inputs yield identical outputs in tests.
- The distribution family, fitting window, and fit error MUST be represented in the model so that
  future work (error propagation, time-based windows, decayed past-season weighting) can be added
  without redesigning the core.

Rationale: Fantasy decisions are tradeoffs under uncertainty; the docs define the model as
distributions aggregated by simulation.

### IV. Explicit Tactical vs. Strategic Context

Every comparison MUST declare which mode it runs in, and the mode MUST change the computation, not
just the labels.

- Tactical (short-term): compare against the current matchup opponent only; the number of games
  scheduled MUST scale each player's contribution.
- Strategic (long-term): compare against every other team in the league; games-played differences
  are de-emphasized, and availability / injury-proneness MUST be accounted for.
- The reported record (e.g. W-L) reflects the single current matchup in tactical mode and the
  aggregate of matchups against every other team in strategic mode, as scored by the active
  format.
- Mode-specific logic MUST live in the core so that every tool and view consumes the same result.

Rationale: The same roster move can be right for this week and wrong for the season; conflating
the two misleads the user.

### V. Glanceable, Difference-First Visualization

Tools are decision aids; their output MUST be readable at a glance.

- The UI MUST follow the overall style in `docs/style.md` ("newspaper meets nutrition label":
  Helvetica Neue only, black/white/yellow chrome, no border-radius, shadows, or gradients, lines
  earned rather than sprinkled, density over progressive disclosure).
- Visualizations MUST prioritize conveying differences (selected team vs. opponent, league
  average, or league leader) over raw detail, with minimal borders, gridlines, and tick marks.
- Data marks MUST use the palettes in `docs/style.md`; the selected team MUST be emphasized and
  comparisons muted via shade or transparency.
- New colors, fonts, or visual idioms require an amendment to `docs/style.md`, not ad hoc choices.

Rationale: The user needs a fast "is this move better?" answer; visual noise and inconsistent
color semantics slow that down.

### VI. Data Source Orthogonality via SQL Schema Contract

Where data comes from MUST be completely independent of the engine and the tools.

- The sole contract between data sources and the rest of the system is a SQL database and its
  schema (players, teams, managers, rosters, games/box scores, schedules, injuries, leagues).
- Data source adapters (any fantasy platform, stats API, CSV, or fixture) MUST only write into the
  schema. They MUST NOT be imported by, or import, the engine, scoring formats, or tools.
- The engine and tools MUST read league and player data only through SQL against the schema. They
  MUST NOT know which source populated it.
- The schema MUST be versioned and changed only through migrations. A schema change is a contract
  change: it requires updated migrations, updated adapters, and passing contract tests.
- Schema SQL MUST stay portable (standard SQL, no vendor-specific features) unless an amendment
  says otherwise.
- Swapping or adding a data source MUST NOT require any change outside the adapter.

Rationale: Data sources are the most volatile part of the system (APIs change, leagues move
platforms); isolating them behind a schema keeps the modeling stable and testable with fixtures.

### VII. Modular Tool Collection on a Shared Core

The repository is a collection of tools (Impact Analysis, Player Potential, and more) built on a
common modeling core.

- Layering MUST be: data adapters → SQL schema → core (data access, distributions, scoring
  formats, simulation) → tools → API → frontend. Dependencies point one way only.
- Shared domain logic MUST live in the core and be consumed by all tools; each tool MUST be
  independently usable and MUST NOT depend on another tool's internals.
- The core MUST be usable and testable without any UI or network access.
- Roster operations (add, drop, swap, reset) MUST be modeled as pure state transitions over a
  league snapshot; original rosters MUST be recoverable ("reset to default"), and hypothetical
  moves MUST NOT be written back to source data.

Rationale: Multiple planned tools share the same statistical foundation; duplicating it invites
inconsistent answers between tools.

## Technology Stack & Architecture

- Backend, core engine, scoring formats, data adapters, and tools MUST be written in Python.
  Numeric work (fitting, simulation) SHOULD be vectorized (e.g. NumPy) rather than per-iteration
  Python loops.
- The backend API MUST be built with FastAPI. It exposes tool results to the frontend over HTTP;
  the frontend MUST NOT access the database directly.
- API request/response models (Pydantic) are the contract with the frontend; frontend TypeScript
  types SHOULD be generated from the FastAPI OpenAPI schema rather than hand-maintained.
- The API layer MUST stay thin: it validates input, calls core/tools, and serializes results. No
  modeling or scoring logic lives in route handlers.
- The frontend MUST be React + TypeScript, built with Vite.
- Charts MUST be built with Observable Plot where it fits (e.g. distribution curves) and D3
  where Plot does not (e.g. radar charts). Chart styling MUST be fully controlled in code to meet
  `docs/style.md`; adding another charting library requires an amendment.
- The frontend MUST NOT re-implement statistical or scoring logic; it renders what the API
  returns.
- Data storage is SQLite. Because the schema MUST stay portable (Principle VI), moving to another
  SQL engine later requires only a connection/config change and migration tooling, not changes to
  the core or tools.

## Domain Scope & Data Constraints

- The default scoring format is 9cat h2h; other formats are added per Principle II.
- Roster sizes are fixed per league. Adding a player MUST only succeed when the roster has an
  empty slot; acquiring a player rostered on another team MUST be expressed as a swap with a named
  counterpart.
- Dropped players MUST move to the free-agent pool.
- Domain terminology (team, manager, roster, free agent, category, matchup, punt, stream) MUST be
  used consistently with `docs/overview.md`.

## Development Workflow & Quality Gates

- `docs/` is the source of truth for domain rules and style. Specs MUST link to the relevant doc,
  and changes to domain rules MUST update `docs/` in the same change.
- Features follow the Spec Kit flow: specify → (clarify) → plan → tasks → implement. Each plan
  MUST include a Constitution Check against Principles I–VII.
- Core changes MUST include automated tests covering: ratio-stat aggregation from components,
  lower-is-better direction, outcome logic including ties, and deterministic simulation output
  under a fixed seed.
- Each scoring format MUST pass the shared format conformance suite.
- The schema MUST have contract tests, and core and tool tests MUST run against fixture data loaded
  through the schema, not against a live data source.
- Tactical and strategic modes MUST each have at least one test asserting their distinct outcome
  computation.
- Any deviation from a principle MUST be recorded in the plan's Complexity Tracking with
  justification.

## Governance

- This constitution supersedes conflicting guidance elsewhere in the repository. Where `docs/`
  and this constitution disagree, the conflict MUST be resolved by amending one of them explicitly.
- Amendments are made via `/speckit-constitution`, MUST include a Sync Impact Report, and MUST
  state the version bump rationale.
- Versioning follows semantic versioning: MAJOR for removing or redefining a principle; MINOR for
  adding a principle/section or materially expanding guidance; PATCH for clarifications and
  wording.
- Compliance is reviewed at plan time (Constitution Check) and at review time for every change
  touching the core, the schema, a scoring format, or visualizations.

**Version**: 1.0.0 | **Ratified**: 2026-10-23 | **Last Amended**: 2026-10-23
