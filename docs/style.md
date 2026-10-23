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

Red `#c00` appears only on destructive actions (e.g. the drop `-` button). It is a warning, not a
design color.

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

No border-radius anywhere; every element is a rectangle. Only real `<button>` elements and inputs
get a border (1px solid `#111`) to signal they are interactive.

### Data density

The UI is for people who want to see a lot at once.

- Table cells use tight padding (0.28–0.3rem vertical, 0.25–0.5rem horizontal); data text ~0.78rem.
- All stat columns are visible; no progressive disclosure for stats. A dense table beats an
  accordion.
- Bench/inactive rows are muted gray so the eye goes to starters first.
- Show `–` (not `0`) for absent stats, to tell "didn't play" from "scored zero".
- Integers for scores and totals; one decimal for averages; percentages to three decimals (`.473`).

### Interactive states

Each interactive element has exactly two states beyond default:

- **Hover** on rows: `#eee` background.
- **Selected / active**: `#f5c518` yellow background.
- **Primary button**: black fill, white text, `#333` on hover.
- **Secondary button** (e.g. `+`, reset, pager): transparent, black border, yellow on hover.
- **Destructive button** (e.g. `-` drop): red border and text, fills red on hover.
- **Disabled**: `#aaa` border and text. **Pending / in flight** (e.g. simulation running): italic
  and 75% opacity.

### Layout

- Content runs close to the viewport edges (~2rem padding). No centered, narrow `max-width`
  containers unless the viewport is very wide.
- Impact Analysis caps the page at 1100px and centers it on wider windows, so content keeps
  its proportions.
- Side-by-side columns when space allows (e.g. roster | radar; main | player picker sidebar),
  without boxes around them.
- Nav is plain text: no borders, pills, or backgrounds; active item marked by weight or underline.

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
- #101F2E;
- #36274E;
- #642E4A;
- #7F4430;
- #7D6831;
- #5C8E4E;
- #44A59F;
- #61B2E7;
- #BCB5F6;

## Distributions and Radar

- **Fills:** a curve's fill uses a lighter shade from the same palette as its line. For example,
  a primary `#1C324A` line gets a primary `#9DC0F5` fill. Overlays sit under the selected team's
  curve.
- **Average markers:** each distribution has a vertical line at its average. Distributions about
  the league (league leader, next best, league average) use a dotted line; team distributions
  use a solid one.
- **Radar:** the selected team uses the primary color with a light primary fill. Other teams
  use the secondary shades, muted, with a faint light-secondary fill. The opponent in tactical
  mode uses secondary `#A96043`.
- **Labels:** each average line is labeled with its role and value. A label moves to another row
  only when it would collide with another label.
- **Name columns:** the player and category columns in tables are bold.

