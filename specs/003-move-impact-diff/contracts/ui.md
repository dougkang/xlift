# Contract: Showing Changes on the Impact Analysis Page

This extends [002 contracts/ui.md](../../002-impact-analysis/contracts/ui.md). All values,
deltas and tones come from `result.changes` (contracts/api.md). The page never compares numbers
itself.

## Delta marker (shared component `<Delta change={…} format={…} />`)

- **Placement:** small text (`--header-size`), normal weight, right after the value, separated
  by a thin space.
- **On the next line (FR-019, revised):** `<WithDelta>` stacks the value (no-wrap) above a
  `.delta-line`. That line is always rendered with a reserved minimum height, even when the change
  is null, so the layout is identical with and without moves.
- **Records:** the W number is colored by its change (`.wins-better` green, `.wins-worse` red). `<WLTDelta>` shows only the change in wins (e.g. `+2`) below a W–L–T record, in its
  tone. The loss and tie changes are not displayed. The API still provides them.
- **Sign:** always shown. Positive is `+`. Negative uses `−` (U+2212), not a hyphen.
- **Precision:** per research R2. Ratios show as `.012` with no leading zero. Percentage-point
  changes (Win %, chance to win) include the `%` sign, e.g. `+13%`. The area score is a 0–100
  score, not a percentage, so it has no sign: `+4`.
- **Color by tone:** `better` is `--better` (`#5C8E4E`), `worse` is `--worse` (`#c00`), and
  `neutral` is `--muted`.
- **Nothing shown** when the Change is null.
- **Accessibility:** `aria-label` reads e.g. "up 2, better".

## Per place (the spec's inventory)

| # | Place | Rendering |
|---|---|---|
| 1 | Headline, strategic | `7–10–0`, with the wins change (`+2`) on the reserved line below, right-aligned |
| 2 | Headline, tactical | `61%`, colored green or red by its change, with `+13%` on the reserved line below |
| 3 | Radar | The selected team's original shape from `radar.original` as a gray dotted outline. The opponent's original is not drawn, (`--before-line`, 1.5px, dash 4,3) over the current shapes. No red/green layers or spoke segments. The default scale is Win % |
| 4 | Radar tabs | `Rank 29` followed by a Delta |
| 5 | Per Category Ranking | A Delta after each of Rank, Avg, League, Leader, Win % |
| 6 | Per Category Difference | A Delta after each of You, Opp, Diff, Win % |
| 7 | Category Breakdown | `selected_original` drawn first, as `--before-fill` areas with **dotted** `--before-line` outlines. The legend lists "<Team> (before)" right after that team's own entry, with a dotted swatch. The average label becomes `You 412.3 +18.0`, with the change in the tone color and no parentheses. Label placement accounts for the longer text, and only uses an extra label row when the labels would otherwise collide, as in 002 |
| 8 | H2H rows | A Delta on each of the H2H W/L/T and Win %. Result: `flip_better` is bold `--better`, `flip_worse` is bold `--worse`, `better`/`worse` are colored but not bold, and the cell's title says "was L" etc. |
| 9 | H2H total | A Delta on each count |

## Tokens (added to `tokens.css`, documented in `docs/style.md`)

```text
--better: #5c8e4e;   --worse: #c00;   --before-line: #aaa;   --before-fill: #eee;
```
