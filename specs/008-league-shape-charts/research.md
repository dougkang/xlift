# Research: League Shape Charts in the Category Breakdown

## R1. Values: the analysis's projected averages

**Decision**: each team's value in a category is its projected per-period average from the
analysis (`Computed.averages`). These are the numbers the Per Category Ranking table and the
radar already show. Ratio categories are ratios of mean makes to mean attempts.

**Rationale**:
- FR-003 / SC-002 require agreement with the ranking table.
- The values already reflect moves and the Fragility Penalty.

**Alternatives considered**: the rankings report's expected-line totals (mean × availability ×
games). It's the same quantity without simulation noise, but it would disagree with the table
by that noise, and it needs a second computation path.

## R2. Places and ties

**Decision**:
- A team's place is its position when teams are sorted by the existing competition rank
  (`ranks(averages, fmt)`), then by team id. So places run 1…N with no repeats, and equal the
  table's rank whenever there are no ties.
- Teams whose value is missing (NaN, e.g. no attempts) are dropped before placing. N is the
  number of teams with a value.
- Hover text shows the table's rank. With a tie, two teams share a rank but take adjacent
  places.

**Rationale**: the spec's edge case (ties take consecutive places in a fixed order, gap 0) and
FR-003 (ranks match the table). Projected averages are continuous, so ties are practically
limited to identical rosters.

## R3. Gaps and the null line

**Decision**: with the values ordered by place, v₁ … v_N:
- **gap** g_r = |v_r − v_{r+1}| for r = 1 … N − 1. The absolute difference equals the difference
  of direction-adjusted keys, so it's never negative and has the same meaning for TO.
- **null gap** n_r = (z_r − z_{r+1}) · σ, where:
  - z_i = Φ⁻¹((N + 1 − i − 0.375) / (N + 0.25)) is Blom's approximation to the i-th largest of N
    standard normal draws;
  - σ is the SD of the N values, with N − 1 in the denominator.
- **No chart** with N < 3, so neither gaps nor null gaps are returned.

**Rationale**: it's exactly the rankings report's computation (SC-003), which uses
`NormalDist().inv_cdf((i − 0.375)/(n + 0.25))` for i = n…1 and `np.std(ddof=1)`. A normal league
has wider gaps at the extremes by geometry alone. The null line makes "the top is expensive"
visible only when it exceeds that.

**Alternatives considered**: the 20,000-league simulated band (the report's percentile table).
It's more than a chart overlay needs, and the line is what you liked.

## R4. Marks

**Decision**:
- The selected team's point is flagged `selected`.
- The gap leading to the team's place − 1 is marked `climb` (the gap it must close to move up
  one place). The gap from its place to place + 1 is marked `cushion`.
- At place 1 there is no climb; at place N there is no cushion.

**Rationale**: FR-006 and FR-007. The server computes the marks, so the frontend only colors
them (FR-011).

## R5. The before marker

**Decision**: with moves in effect, the tool passes the original analysis (`reuse`, already
computed for the before/after diff) to the shape builder. The selected team's original place
and value per category become `before`, placed within the original league by the same rule
(R2). Without moves, or if the original value is missing, `before` is null.

**Rationale**: FR-010. It costs nothing extra: the original's averages and ranks are already in
memory.

## R6. API shape

**Decision**:
- `AnalysisResult.league_shape: list[CategoryShape] | null`. It's null in tactical mode, for an
  unsupported format, and when nothing was simulated.
- One `CategoryShape` per category, in `categories` order:
  - `category`;
  - `teams`: [{team_id, team_name, place, rank, value, selected}], by place;
  - `gaps`: [{to_place, gap, null_gap, mark}], empty when N < 3;
  - `before`: {place, rank, value} | null.

**Rationale**:
- A separate field rather than a change to `curves`: curves are shared with tactical mode, and
  this is strategic only.
- An additive, nullable field keeps older clients working.
- Ordering by place lets the frontend draw without sorting.

## R7. Charts and style

**Decision**: each category's figure gets two small **hand-drawn SVG** charts under its
distribution, scaled with `d3-scale` like the radar (`Radar.tsx`), at the cell's measured width
(~90 px tall each). Every point and bar is its own element, so it carries `data-*` attributes
and a `<title>` tooltip, which tests can check. Colors use the theme's CSS variables (`--sel`,
`--other-*`, `--avg`) where they fit, with `--gap`, `--climb` and `--cushion` added next to them
for the values below:

- **League shape**:
  - points joined by a thin line in secondary `#F5C1A9`, other teams' points in secondary
    `#CE7955`;
  - the selected team's point in primary `#1C324A`, larger and drawn last;
  - the before marker as a hollow `#aaa` circle;
  - x = place (1 at the left), y = value (not zero-based), minimal ticks.
- **Against null**:
  - bars in light secondary `#F5C1A9`;
  - the climb bar in primary `#1C324A` and the cushion bar in primary light `#9DC0F5`;
  - the null line in tertiary `#898240`, dotted (a league reference, like the League Average
    line).
- **Formatting**: values and gaps use the category's decimals (`.473` style for ratios; one
  decimal for counts), via the existing formatter.
- **Tooltips**: an SVG `<title>` on each point and bar. Points show name, rank and value; bars
  show "to place r", the gap and the null gap.
- **Style guide**: `docs/style.md` gains a short "League shape" subsection describing the two
  idioms and their colors (Constitution V: new idioms are documented).

**Rationale**:
- It uses the palettes the style guide defines. The selected team is emphasized and comparisons
  are muted, per Principle V.
- **Observable Plot** (used by the distribution curves) was rejected for these two charts. Its
  marks can't carry per-datum attributes, so the selected, climb, cushion and before marks
  couldn't be tested.
- **Alternatives considered**: a separate section below the breakdown. It was rejected because
  you asked for the charts in the breakdown; keeping them in each category's block reads
  category by category.
