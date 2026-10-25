# UI Contract Changes: League Shape Charts

Base: [002 ui.md](../../002-impact-analysis/contracts/ui.md). Style per `docs/style.md`, with
the amendment this feature adds. Help text never mentions file names (project rule).

## Category Breakdown (strategic mode)

Each category's block keeps its distribution chart and adds two small charts below it, at the
same width:

1. **League shape**: x = place (1 at the left), y = value.
   - Other teams: secondary-shade points joined by a thin light-secondary line.
   - The selected team: a larger primary `#1C324A` point, drawn on top.
   - With moves: a hollow `#aaa` circle at the team's pre-move place and value.
   - Hover a point: "Team · rank N · value".
2. **Against null**: one bar per gap, x = the place it leads to.
   - Bars are light secondary.
   - The **climb** (the gap to move up one place) is primary `#1C324A`.
   - The **cushion** (the gap to the team below) is primary light `#9DC0F5`.
   - A dotted tertiary `#898240` line shows the null gaps.
   - Hover a bar: "to place r · gap · normal gap".

The charts carry no captions; the help describes them. Values use the category's
format (`.473` for ratios, one decimal for counts). A category with fewer than three teams with
values shows only League shape.

Tactical mode: unchanged (no league-shape charts).

## Help (Category Breakdown)

Reading lines added, strategic only, within the 120-word limit:

- "Below each, the line shows every team's projected value by place; your dot is navy (hollow
  gray: before your moves)."
- "The bars show the gap to reach each place. The dotted line is the gap a normally spread league
  would show; bars above it are cliffs, below it clusters. Navy is your gap to climb a place;
  light blue, your cushion over the team below."
