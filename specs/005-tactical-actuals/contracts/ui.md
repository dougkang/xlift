# Contract: UI changes

## Settings

- **Removed:** the **vs** and **Week** controls.
- **Mode toggle:** **Tactical** is disabled when `league.current_matchup` is null. Its `title`
  reads "This week's matchup hasn't been loaded yet". No user-facing text names data files.

## Headline (tactical)

```text
Week 1 · Oct 19–Oct 25 · Now 5–4–0                     Chance to Win ?
Keyboard Cats  Doug Kang                                          33%
vs. Triton Aggies
```

The as-of date appears under the intro as "Matchup last updated: <date>", one per line with the
statistics and rosters dates.

- **Current score:** "Now W–L–T" comes from `header.matchup.current`. The W follows the existing
  `Wins` coloring.
- **Final:** once `final` is true, the line reads "Final 5–4–0", and Chance to Win shows the
  certain result.
- **Layout:** the record keeps its baseline alignment with the team name (style tweaks, f365687).

## Per Category Difference (tactical)

| Category | Now (You–Opp) | You | Opp | Diff | Win % |
|---|---|---|---|---|---|

- **Now:** the week-to-date pair in muted text, e.g. `74–68`. Ratios use the category's
  decimals.
- **You / Opp:** now the projected **final** values. Diff and Win % are unchanged.

## Opponent's roster (tactical, replacing H2H)

- **Title:** a section divider with the opponent's team name and `<HelpButton topic="opponentRoster" />`.
- **Columns:** the same as the selected team's Roster (Player, Pos, G), with reserve rows muted,
  status in red, and footnote markers.
- **Read-only:** no drop column and no row actions. It is rendered by `Roster` with
  `onDrop` left undefined.

## Help (004 content updates)

- **`settings`:** drops vs and Week.
- **`mode`:** says tactical is always your current matchup from the imported `matchups.csv`.
  Totals are actual so far plus projected remaining games.
- **`headline` (tactical):** adds "Now" (the current score) and the as-of date.
- **`categoryTable` (tactical):** adds Now as the week-to-date values. You and Opp are projected
  finals.
- **New `opponentRoster` topic:** your opponent's roster; read-only, because moves apply only
  to your team.
- **Limits:** every topic stays at 120 words or fewer.
