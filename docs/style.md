# Style Guide

## Overall Style

We adopt the design philosophy of the ccsv-rumble-page (origin:
`~/dev/design-philosophy/design-philosophy.md`). The base philosophy applies, not that project's
own amendments. It is summarized here; the sections after this one extend it for data
visualization.

The theme is **newspaper meets nutrition label**: clean and easy to read even when the data is
dense. Every visual decision serves legibility first. The reference point is a well-formatted
sports statistics page.

### Color (UI chrome)

Three colors only for UI chrome (text, structure, controls):

- **Black `#111`**: text, borders, primary buttons, structural lines. The default ink.
- **White `#fff`**: background. Nothing else.
- **Yellow `#f5c518`**: the single accent. It means "yours" or "selected" (the selected team,
  selected rows, active mode toggle). It is never decorative, and never a primary-button color.

Red `#c00` is a warning, not a design color. It appears only in these places:
- destructive actions on hover, e.g. the drop `−` button;
- a player's availability status (Q, O, DTD, IL, NA, …), shown as small bold red text after the
  player's NBA team;
- a change for the worse after a roster move (see "Change (before/after)");
- a losing record in the each-category H2H table (its winning records are green).

Green `#5C8E4E` means "good for you" everywhere: a change for the better, the tactical
Diff column when the difference favors you, and a winning record in the each-category H2H
table. Red marks the opposite.

Grays (`#555`, `#888`, `#aaa`, `#ccc`, `#eee`) mean muted state only: bench rows, inactive
links, placeholders, disabled controls. Gray means secondary or unavailable.

Before reaching for a new color, ask whether black, yellow, or gray already says it.

Colors inside charts (data marks) come from the palettes below, not from this list.

### Typography

One font: **Helvetica Neue**, including chart labels. No icon fonts, display fonts, or web fonts.
Weight and size alone create hierarchy; color never does.

Heading levels, each with one job:

1. **Masthead** (page/tool title): large (~3rem), weight 800–900, left-aligned, negative
   letter-spacing, thick black rule below. One per page.
2. **Section divider**: centered, ALL CAPS, bold, ~2px letter-spacing, full-width black rule below.
3. **Headline** (e.g. "Team Name 5-4"): left-aligned, ~800 weight, larger than body, no decoration.
4. **Sub-headline / block label** (e.g. a team or roster label): bold, normal case, ~body size.
5. **Column header** (e.g. "PTS REB AST"): ~0.65rem, ALL CAPS, weight 900, muted gray,
   right-aligned over numeric columns.

Rules:

- Italic only for quoted opinions and loading/placeholder states.
- ALL CAPS only for nav links, section dividers, and column headers.
- Tight or negative letter-spacing only on the masthead.

### Lines and borders

Use as few lines as possible. Whitespace separates rows, not rules.

- Lines in use: a rule under the masthead; a 1px `#111` rule under a table's column header row; a
  1px `#ccc` rule only where two sections meet with no gap.
- Absent: row separators in table bodies, card/panel borders, box shadows, gradients.

Before adding a line, ask whether more padding does the same job.

### Shape

No border-radius anywhere; every element is a rectangle. Controls are not boxed:
- **Buttons** have no visible border.
- **Inputs and selects** show only a light `#ccc` bottom rule, which darkens to `#111` on hover.
  Dropdowns drop the browser's native look and use a small muted chevron, which darkens on
  hover, so they read like the search bar.

Keyboard focus always shows a 1px `#111` outline.

### Data density

The UI is for people who want to see a lot at once.

- Table cells use tight padding (0.28–0.3rem vertical, 0.25–0.5rem horizontal); data text ~0.78rem.
- All stat columns are visible; no progressive disclosure for stats. A dense table beats an
  accordion.
- Bench/inactive rows are muted gray so the eye goes to starters first.
- Show `–` (not `0`) for absent stats, to tell "didn't play" from "scored zero".
- Integers for scores and totals; one decimal for averages; percentages to three decimals (`.473`).

### Interactive states

**The visualization is the priority; controls stay quiet until you reach for them.** Each
interactive element has exactly two states beyond default:

- **Default**: controls are muted. Buttons are borderless, with muted `#555` text. Row actions
  (`+` add, `−` drop, Give) sit at 35% opacity.
- **Hover / focus**: the control reveals itself with a fill.
  - Hovering a row brings its row actions to full opacity and gives the row an `#eee` background.
  - A hovered button fills yellow `#f5c518` with `#111` text.
  - A hovered destructive button (`−` drop) fills red `#c00` with white text. Red appears only on
    hover, never at rest.
- **Selected / active**: `#f5c518` yellow background, for example the active mode pill.
- **Primary button** (rare): black fill, white text, `#333` on hover.
- **Disabled**: `#ccc` text with no fill on hover. A tooltip explains why.
- **Pending / in flight** (e.g. a simulation running): italic and 75% opacity.

### Help

- **Button**: a muted "?" at header size, right-aligned: at the right end of a section divider
  (out of flow, so the title stays centered), after the headline's unit label, right after the Strategic / Tactical
  toggle, or at the far right of the settings row. It's a
  quiet control (yellow on hover) and never adds a line or shifts the layout.
- **Popup**: anchored below its button (above when there's no room), at most 22rem wide, kept
  16px inside the viewport and scrolling when tall. It has a 1px `#111` border, a
  slightly cream `#FFFBF0` background so it stands apart from the page, and no radius or shadow.
  - It has a bold title with a 1px `#111` rule under it, like a section divider, then
    column-header labels: **Controls**, **Reading it**, **Terms**.
  - Body text is at data size, with control and term names in bold.
- **Copy**: at most 120 words per popup, Controls first. All copy lives in
  `frontend/src/help/content.ts`.

### Layout

- Content runs close to the viewport edges (~2rem padding). No centered, narrow `max-width`
  containers unless the viewport is very wide.
- Impact Analysis caps the page at 1100px and centers it on wider windows, so content keeps
  its proportions.
- Side-by-side columns when space allows (e.g. roster | radar; main | player picker sidebar),
  without boxes around them.
- Nav is plain text: no borders, pills, or backgrounds; active item marked by weight or underline.
- **Tool nav:** plain-text ALL CAPS links above the masthead, one per tool; the current tool is
  bold and underlined, the others muted `#555` (black on hover). Player Analysis uses the same
  1100px page as Impact Analysis.

### What this is not

- Not a dashboard product: no cards, KPI tiles, or progress bars.
- Not a consumer app: no rounded corners, drop shadows, or illustrations.
- Not minimal or blank: data fills the space; emptiness is a loading state.
- Not heavily gridded: lines are earned, not sprinkled.

For visualizations, we extend the design philosophy as follows.

## Visualizations

Visualizations should be simple and readable at a glance.
Minimize borders and tick marks.  The primary objective would be to convey differences.

## Lower Dimensional Palettes

Used https://supercolorpalette.com/

For simple categorizations with 3 dimensions or less, the colors in each of the
primary, secondary, and tertiary color lists should be used.

Shade denotes importance. The darker the shade, the more important it is perceived to be.

Primary Colors:
- #101F2E;
- #1C324A;
- #264567;
- #315986;
- #3C6CA6;
- #4A80C5;
- #5F95DE;
- #7CABED;
- #9DC0F5;

Secondary Colors:
- #391F16;
- #5D3425;
- #824934;
- #A96043;
- #CE7955;
- #E89A78;
- #F5C1A9;

Tertiary Colors:
- #342F17;
- #504A25;
- #6C6532;
- #898240;
- #A79F4E;
- #C5BE60;

## Simple, Qualitative Categorization with higher Dimensions

These colors should be used for any qualitative coloring with higher dimensionality where there is absolutely
no relationship between categories.
- #a6cee3;
- #1f78b4;
- #b2df8a;
- #33a02c;
- #fb9a99;
- #e31a1c;
- #fdbf6f;
- #ff7f00;
- #cab2d6;

## Distributions and Radar

- **Fills:** a distribution is a fill only, with no outline, in a lighter shade from the same
  palette as its average line. For example, a primary `#1C324A` average line goes with a primary
  `#9DC0F5` fill. Overlays sit under the selected team's curve; the before-moves distribution is
  the gray `#eee` fill behind everything.
- **Average markers:** each distribution has a vertical line at its average. Distributions about
  the league (league leader, next best, league average) use a dotted line; team distributions
  use a solid one.
- **Radar:** the selected team is drawn last, filled solid in its primary border color. Any team
  inside our area is hidden, so only categories where another team beats us show through. Other teams
  use the secondary shades as muted outlines, with a faint (15%) light-secondary fill. In strategic mode, the League Average
  (`#898240`) is a dotted outline, matching the breakdown's average line, with a legend under
  the radar. The opponent in tactical mode uses secondary
  `#A96043`.
- **Labels:** each average line is labeled with its role and value. A label moves to another row
  only when it would collide with another label.
- **Name columns:** the player and category columns in tables are bold.

## League shape

Two small charts under each strategic category's distribution, at the same width, without
captions (the help names them). No gridlines; the x axis shows only the first and last place.

- **Rank ladder (League shape):** one point per team at (place, value), joined by a thin
  light-secondary line (`#F5C1A9`). Other teams' points are secondary `#CE7955`; the selected
  team's point is primary `#1C324A`, larger, drawn last. With moves, the selected team's
  pre-move position is a hollow `#aaa` circle, like the "before" distribution.
- **Gap bars against a null line (Against null):** one bar per gap between adjacent places, in
  light secondary `#F5C1A9`. The selected team's climb (the gap to move up a place) is primary
  `#1C324A`; its cushion (the gap to the team below) is primary light `#9DC0F5`. The null line
  is dotted tertiary `#898240`, like the League Average line, since it's a league reference.
- **Tooltips:** each point and bar has a title with the team (or place), rank and formatted
  value.

## Leaderboard (stacked bars)

Player Analysis ranks players with one horizontal bar each, split into the categories the value
comes from.

- **Rows:** one per player in the server's order (best first), about 18px each. To the left, in
  data size: the name in bold, the owner muted ("Free agent" or the team), the status in red, and
  the signed net right-aligned (`+1.84`, `−0.12`, real minus sign), then `*` for a short history.
- **Segments:** one per category, filled from the qualitative palette above in the format's
  category order, with no borders. Gains stack right of zero, losses left of it. A legend of
  swatches above the chart names the categories.
- **Zero:** a 1px `#ccc` rule.
- **Net:** a 2px `#111` tick over a 4px white one, so it reads on every segment, light or dark
  (`#1f78b4`).
- **Axis:** x only, at the top, a few ticks, labeled with the unit; no gridlines.
- **Tooltips:** each segment's title is "Player · Category · value"; the tick's is "Player ·
  xLift value", both signed to two decimals.
- **Empty:** "No players match these filters." in italic muted text replaces the chart.

## Current matchup (tactical)

- **Score so far:** "Week N · Mon D–Mon D · Now W–L–T" is a muted line at data size above the
  team name ("Final W–L–T" once the week is over). The opponent line below the team name reads
  "vs. Opponent".
- **Last updated:** under the intro, one date per line: statistics, rosters and, once loaded, the
  matchup.
- **Now column:** the Per Category Difference table's first value column holds the week-to-date
  pair, you–opponent, in muted text. Counts are whole numbers; ratios use the category's format.
  You, Opp and Diff are the projected finals.
- **Opponent's roster:** in tactical mode it replaces H2H, titled with the opponent's team name.
  It uses the Roster table style with no drop buttons, because moves apply only to your team.
- **No matchup imported:** the Tactical toggle is disabled, with the tooltip "This week's
  matchup hasn't been loaded yet". User-facing text never names data files.

## Change (before/after)

After a hypothetical roster move, every projected value is compared with the original roster
(no moves).

- **Better:** green `#5C8E4E`.
- **Worse:** red `#c00`.
- **Neutral:** muted `#555`, for changes that are neither good nor bad for the selected team
  (ties, league averages).
- **Deltas:** small text (0.65rem), normal weight, on the line directly below the value: `+2`,
  `−1`, `+18.0`, `+.012`. Percentage changes include `%`, e.g. `+13%`.
  - That line is always reserved, so nothing moves when changes appear.
  - W–L–T records show only the change in wins (e.g. `+2`). The W number itself is colored too:
    green when wins went up, red when they went down. The tactical Chance to Win
    percentage is colored the same way by its change.
  - Chart labels are the exception: there the change follows the label inline.
  - Negative values use a real minus sign `−`.
  - No parentheses in tables.
  - Nothing is shown when the change rounds to zero at the value's display precision.
- **Bold:** only for a result that flips between W and L. L→W is bold green, W→L bold red. Any
  other better or worse result change is colored, not bold.
- **Original (before) visuals:**
  - Radar: your team's original shape is a gray dotted `#aaa` outline over the current shapes,
    with no outline for the opponent. There are no colored fills for change.
  - Distributions: the original is a light `#eee` area with a dotted `#aaa` outline, drawn
    behind everything else. The legend labels it "<Team> (before)", right after the team's own
    entry.
- **Layout never changes:** values never wrap, and the change line is reserved even with no
  moves. Showing markers never moves a section.

