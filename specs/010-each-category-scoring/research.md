# Research: H2H Each-Category Scoring

## R1. Where the standings rule lives

**Decision**: both of the issue's options. `ScoringFormat` gets a declared field,
`standings: Literal["matchup", "category"] = "matchup"`, and `nine_cat.py` registers a second
format, `9cat_h2h_each` ("9-category head-to-head, each category"), built with
`dataclasses.replace(NINE_CAT_H2H, id=..., name=..., standings="category")`.

**Rationale**: Constitution II wants win rules in the format and tools that depend only on the
interface. With the rule as a field, tools branch on `fmt.standings`, never on a format id, and a
future each-category 8cat is one more registration. The existing `9cat_h2h` keeps its default, so
its behavior and output are untouched (FR-020). The league already stores a format id, so the
league picks its rule with no schema change.

**Alternatives considered**:
- *Only a new format id, tools check the id*: violates II (hard-coding a format outside a format
  module).
- *A per-league setting column*: a schema change (VI) for something that is a property of the
  scoring format.
- *A callable rule returning each simulation's (W, L, T)*: more general, but the expected record
  is the per-category odds the engine already computes (R2); a callable adds nothing the two
  rules need.

## R2. Expected record

**Decision**: a new core function `expected_record(odds: Iterable[Odds]) -> ExpectedRecord` in
`core/sim/engine.py`: W = Σ P(win), L = Σ P(loss), T = Σ P(tie) over categories, as floats, with
`win_pct = (W + ½T) / (W + L + T)` (0 when the total is 0). It sums records too
(`ExpectedRecord.__add__`), for the strategic total.

**Rationale**: under each-category the standings contribution of a matchup is exactly the
per-category outcome counts; their expectation is the per-category odds. The odds are already
computed from the same `fmt.compare` outcomes as the radar's Win %, so the strategic win % equals
the mean radar Win % for the selected team (SC-001) by construction. Each opponent's W + L + T is
the category count, because the three odds sum to 1 per category (SC-002).

`engine.record()` (the > 0.5 cutoff) stays as is: most-categories output uses it and must not
change (FR-020).

## R3. Result shape: added fields, nothing removed

**Decision**: the analysis result gains fields; existing ones keep their meaning under
most-categories and become null where they have none under each-category.

- `standings: "matchup" | "category"` at the top level (FR-006).
- `header.expected_record: {wins, losses, ties, win_pct} | null`: set under each-category in both
  modes; `header.record` is null then. Under most-categories, `expected_record` is null and
  `record` is as today.
- Each H2H row gains `expected_record`; `result` becomes nullable (null under each-category).
- `matchup_totals` gains `expected`; `matchups` becomes nullable (null under each-category).
- `changes.header` gains `expected_wins` and `win_pct`; each `changes.matchups` row gains
  `expected_wins`, with `original_result` and `transition` nullable; `changes.matchup_totals`
  gains `expected_wins`, with `matchups` nullable.

**Rationale**: keeps the most-categories response a superset of today's (only null additions), so
the existing snapshot fixtures stay valid regression checks once the new keys are dropped, and the
frontend branches on `standings` alone.

**Alternatives**: a union type per rule: cleaner types, but a much larger diff to the frontend and
the change builder for no user-visible gain.

## R4. Precision of record changes

**Decision**: records display in **whole categories that add up**, as the style guide asks of
scores and totals. Each opponent's expected record is split into whole W, L and T summing to the
category count (`whole_record`: floors, then the leftover categories to the largest fractions,
ties W, L, T); the strategic Total and headline are the sum of those rows. Rounding each part
alone was tried first and showed rows like 4–4–0 (eight categories), ties that vanished from
rows but not the Total, and a Total that wasn't the sum of its rows. The API sends the whole
record as `record` next to the unrounded values. The expected-wins change is the difference of
the whole wins, so it always matches the numbers on screen; the win % change is in whole points (the existing
`PCT_DECIMALS`, scale 100), which still shows moves under one win. (First built at one decimal;
changed at the user's request: "lets round to whole numbers".)

**Rationale**: `COUNT_DECIMALS = 0` would round a +0.4-win move to nothing (SC-003). One decimal
matches the app's count averages.

## R5. Tactical headline

**Decision**: under each-category the tactical headline is `expected_record` from the current
matchup's per-category odds (the simulation already adds week-to-date totals), shown as
"Projected Record 5.6–3.1–0.3". `matchup_win_probability` is still returned (data), but the page
shows it only under most-categories. When the week is final every simulation equals the final
totals, so the expected record equals the final score (US3 AS2).

## R6. Unknown format at load time

**Decision**: the `ffm load roster` command checks `--format` against `available_formats()` before
calling the adapter and exits non-zero with the known list. The adapter itself doesn't import
scoring (Constitution VI). The adapter already keeps an existing league's format when `--format`
isn't given (FR-021), so the daily script needs no change.

## R7. Regression protection for most-categories

**Decision**: before changing code, record a pre-010 snapshot (`tests/fixtures/pre010_impact.json`)
of full analysis results for the fixture league: strategic, tactical, and both with a move. A test
compares today's results with the new keys (`standings`, `header.expected_record`, rows'
`expected_record`, `matchup_totals.expected`, the new change fields) removed. Existing snapshot
fixtures (`pre007`, `pre009`) aren't regenerated.

## R8. Frontend

**Decision**: `RecordHeadline` and `RecordTable` branch on `result.standings`.

- Headline (category, strategic): label "Aggregated Record" (the combined H2H score, equal to the H2H Total), value `W–L–T` in whole numbers, then the
  win % ("56%") on the line under it with the expected-wins change; the wins number colored by its
  change as today.
- Headline (category, tactical): label "Projected Record", value in whole numbers, change below.
- H2H table (category): columns Opponent | Record; Total row: the summed record. (A Win % column
  was first built and removed at the user's request; the headline keeps the win %.)
  No Result column.
- A small `formatRecord` helper in `format.ts` formats one-decimal records (display only, no
  arithmetic).
- Help topics `headline` and `h2h` take a `standings` field in the help context.

## R9. Docs

`docs/overview.md`: describe both rules, the league's (each category), and how the app reads the
format. `docs/tool1-impact-analysis.md`: the headline and H2H under each rule, the "5 categories"
line and the punting note revised. No style change (same text and color idioms).
