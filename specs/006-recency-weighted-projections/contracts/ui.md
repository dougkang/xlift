# UI Contract Changes: Recency-Weighted Player Projections

Base contract: [002 ui.md](../../002-impact-analysis/contracts/ui.md). Style per
`docs/style.md`; nothing visual changes.

## Controls

- **Last X games** input: the default value becomes **82**. The range is unchanged.

## Help: Analysis settings → "Last X games"

Replaces the current line. Following the project memory rule, it mentions no file names.

> **Last X games**: the most games each projection draws on (now *X*); recent games count more,
> and last season's count less. Small samples are pulled toward a typical player.

## Footnote

Unchanged rule and wording: "* N of X games" when a player has fewer games than *X*.
