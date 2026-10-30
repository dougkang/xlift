# UI Contract: Player Analysis (009)

## Navigation (both tools)

A plain-text nav above the masthead: `IMPACT ANALYSIS   PLAYER ANALYSIS`, all caps (nav links,
per the style guide), with no borders or pills. The current tool is bold and underlined; the other
is muted `#555` and turns black on hover. The links are hash links (`#/`, `#/player-analysis`).

## Page

1. **Masthead**: "Player Analysis".
2. **Explainer** (one line): "Find the players worth adding: who adds the most weekly category
   wins, and in which categories."
3. **Section rule.**
4. **Controls**, one per line (changed after implementation, at the user's request):
   - Shared with Impact Analysis (no Reset, no Team): **Last** _n_ **games**, **Fragility Penalty**,
     **League**, with the help button (topic `playerAnalysisSettings`) at the right of the first.
   - **Evaluate for**: one dropdown with **League** first, then every team ("Team — Manager").
     Picking a team scores for that team and sets the team shared with Impact Analysis; League
     switches to the league average and keeps the last team.
   - **Pool** (Free agents | All players | each team) as a dropdown (amended 2026-10-29; the
     evaluated team lists its own roster, valued against its weakest); **Show top** (10–50 by 5); **Min games**
     (1–15).
   - Under the intro, when the data was loaded (statistics and rosters), as in Impact Analysis.
5. **Moves note** (only when the session has Impact Analysis moves), muted and at data size: "The
   leaderboard uses rosters as they are, without your Impact Analysis moves."
6. **Section divider**: "XLIFT LEADERBOARD", with a help button (topic `leaderboard`).
7. **Scope line**, muted: "Scored for _Team name_" or "Averaged over every team but the player's
   own"; then "_shown_ of _total_ players".
8. **Legend**: one swatch and label per category, in format order.
9. **Chart** (below).
10. **Footnotes**: the asterisk notes, as in Impact Analysis.

While a request is in flight, the chart is in the style guide's pending state (italic, 75%
opacity). An error shows in the app's error style.

## Chart

- One row per entry, in the server's order, top to bottom, about 18px per row.
- **Row label**, to the left of the bars:
  - the **name**, in bold;
  - then the owner, muted ("Free agent" or the team name);
  - then the status in red, as the roster shows it.
  - The net xLift is right-aligned in a fixed column, signed, two decimals, real minus sign
    (`+1.84`, `−0.12`), then the asterisk if the player has a footnote.
- **Bars**: one segment per category, filled from the qualitative palette in format order.
  Positive segments stack rightward from 0, negative ones leftward (`by_category` as given).
  Segments have no borders.
- **Tick** at the net: `#111`, 2px, over a 4px white tick, the row's height.
- **Zero rule**: 1px `#ccc`.
- **Axis**: x only, at the top, few ticks, label "Weekly category wins added"; no gridlines.
- **Tooltip** on a segment: "_Player_ · _Category_ · +0.31" (two decimals). On the tick: "_Player_
  · xLift +1.84".
- **Empty**: when `entries` is empty, the chart is replaced by "No players match these filters."

## Help (≤ 120 words each, no file names)

- **`leaderboard`**:
  - **Reading it**: each bar is one player's xLift, split into the categories it comes from.
    Segments right of zero add wins; left of zero, cost them. The tick is the net.
  - **Terms**: xLift (shared with Impact Analysis).
- **`playerAnalysisSettings`** (the page's only settings help, covering every control):
  - **Controls**:
    - **Last** and **Fragility Penalty**: as in Impact Analysis.
    - **League**: whose league to rank players in.
    - **Evaluate for**: a team scores each player for that team, replacing its weakest active
      player; it's also the team Impact Analysis opens. **League** averages that over every team
      but the player's own.
    - **Pool**: free agents, all players, or one team's players.
    - **Show top**: how many players are shown.
    - **Min games**: hides projections built on fewer games.

## Impact Analysis changes

Only the navigation above its masthead. Everything else is unchanged (SC-007).
