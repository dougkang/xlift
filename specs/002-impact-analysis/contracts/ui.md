# Contract: Impact Analysis Page Layout

This is the UI contract for `frontend/`. Visual rules come from `docs/style.md` and are not repeated
here. Every number and every enabled or disabled state comes from the API (contracts/api.md). The
page applies no domain rules of its own.

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ IMPACT ANALYSIS (masthead, 4px rule)                                                     │
│ See how adding, dropping, or swapping players changes your team — this week or long-term.│
│ League [▾]  Team [▾]  Mode [Strategic|Tactical]  Last [15] games  (Opponent [▾]  Week …) │
│ [Reset]                                       Data: NBA 10-23 20:51 · Rosters 10-23      │
├─────────────────────────────────────────────────────────────┬────────────────────────────┤
│ Triton Aggies — Jung                         11–5–1         │ PLAYERS                    │
│ (record headline; tactical adds "62% to win")               │ [search…………………]           │
├──────────────────────────────┬──────────────────────────────┤ + Free Agent Fred  DAL FA  │
│ ROSTER                       │ RADAR (ranks, rank 1 = rim)  │ + Jalen Brunson   NYK Woo… │
│ − Luka Dončić   LAL  G,F     │                              │   …                        │
│ − AJ Dybantsa*  WAS  F   NA  │ CATEGORY  RANK / DIFF        │                            │
│ …                            │ PTS 2 · REB 5 · …            │                            │
├──────────────────────────────┴──────────────────────────────┤                            │
│ CATEGORY BREAKDOWN (9 small curves, 3 × 3)                  │                            │
├─────────────────────────────────────────────────────────────┤                            │
│ * 0 of 15 games — AJ Dybantsa                               │                            │
└─────────────────────────────────────────────────────────────┴────────────────────────────┘
```

| Region | Behavior | Spec |
|---|---|---|
| **Masthead and explainer** | The heading "IMPACT ANALYSIS" and one sentence of explanation | FR-028 |
| **Controls** | Mode toggle (Strategic / Tactical) is right-aligned on the masthead line. Then four rows: (1) Last X games; (2) League; (3) Team, plus "vs" opponent in tactical; (4) Week (tactical) and Reset. Tactical adds "vs" (an opponent select) and "Week" (start/end dates, defaulting to the server's Mon–Sun period from `settings`). Changing any control re-runs the analysis. Tactical-only controls (opponent, period) appear only in tactical mode. The window field is debounced by 250 ms | FR-001–FR-004, FR-025 |
| **Reset** | Clears the move list. Disabled when there are no moves | FR-023 |
| **Data line** | Shows `freshness` on its own line at the end of the description, in column-header style: "Statistics last updated: … · Rosters last updated: …", followed by a soft 1px #ccc rule that separates the description from the tool | FR-005 |
| **Record headline** | A subheader spanning both the main area and the sidebar, with a 1px rule below. Left: the team name (large) with the manager beside it on the same line (smaller, muted). Right-aligned: the label "Aggregated Record" (tooltip: W–L–T vs N teams) with the record (large) below it. Team, manager and record, with a units label ("vs 17 teams" or "categories vs <opponent>"). Tactical shows "vs. <opponent>" (h3) under the team name, and on the right the chance to win the matchup (large, e.g. "66%") under the label "Chance to Win", instead of the category record. Shows "Choose an opponent" when `OPPONENT_REQUIRED` | FR-014 |
| **Roster** | Right-hand column (swapped with the radar per user preference, 2026-10-23). Player names in bold. One row per player of the selected team, with an unboxed "−" on every row. It is muted until the row is hovered, then fills red on hover. Columns are Player and Pos. The NBA team follows the name on the same line (muted), then any non-healthy status in small bold red. Reserve rows are muted. `games_remaining` is shown in tactical mode. A short history gets an asterisk. Rows changed by moves are marked in the yellow "yours" color | FR-018, FR-019 |
| **H2H** (section) | Below the roster and its footnotes. One row per opponent: name (bold) with the manager, projected category W–L–T (column "H2H"), win %, and the result (W/L/T, by the more-than-half rule). A footer row totals the categories W–L–T and the matchups W–L–T; the matchup total equals the headline record. In tactical mode the table stays league-wide: every opponent, under tactical scaling. The chosen opponent's row is highlighted in yellow and matches the headline. All values come from the API (`matchups[].category_record`, `matchups[].result`, `matchup_totals`) | FR-014 |
| **Radar** | A "Rank | Average | Win %" toggle sits under the Radar heading. Rank: rank 1 at the rim. Average: each category's projected average, min-max scaled across the league by the server (`radar.series[].normalized`, 1 = best, direction applied), at the rim. Win %: the chance of beating a random league opponent in that category (`radar.series[].win_rate`, ties count half), with 100% at the rim and 0% at the center. Each tab also shows the selected team's radar area score under that scale (`radar.series[].area`): its area relative to the league's largest, shown as a 0–100 score where the top team is 100. The API sends a 0–1 fraction. The area depends on category order, since adjacent spokes are multiplied. D3, centered in the left column with the category table below it. One axis per category. The selected team is drawn last with a solid primary fill (the same color as its border), so only teams that beat it in a category show beyond its area. Other teams use muted secondary shades with a light secondary fill (`#F5C1A9`, 12%), and the opponent is secondary `#A96043`. Hovering an axis shows the selected team's rank | FR-015 |
| **Category table** | Strategic (sub-header "Per Category Ranking", below the radar): category label (bold, unlabeled column), Rank, Avg, League (league average), Leader (leader average; tooltip names the team), Win % (chance of beating a random league opponent in the category, `win_rate`). Tactical (sub-header "Per Category Difference"): You, Opp (tooltip: opponent name), Diff, and Win % (`win_probability`, your chance of winning that category vs the opponent). Diff is signed and colored by the side it favors: green for you, red for the opponent, muted when even (changed by 003). Ratios show 3 decimals as `.473` | FR-016 |
| **Category breakdown** | Plot. One small density chart per category. Fills use the lighter palette shade, and each curve has a vertical average line: solid for teams, dotted for league-related curves. Each line is labeled with its role and value (e.g. `You .471`, `League .465`). Labels sit in a single row above the plot. A label moves down to another row only when it would collide with one already placed. The legend names the leader, next best, league average or opponent | FR-017 |
| **Player picker** | Search box plus a paged list (50 per page). Each row shows `+`, name with the NBA team beside it on the same line (muted), then any non-healthy status in small bold red, a Pos column, owner (or FA), games remaining (tactical), and an asterisk. `+` is disabled when `can_add` is false and no swap option exists, with `add_blocked_reason` as its title. For a rostered player, `+` opens the swap dialog | FR-020, FR-021, FR-026, FR-027 |
| **Swap dialog** | "Give <team> one of:" followed by the selected team's roster (when `roster` is allowed) and a free-agent search (when `free_agent` is allowed). Confirming appends a `swap` move | FR-021 |
| **Footnotes** | Every `footnotes` entry, directly below the roster table | FR-007 |
| **Errors** | A 422 move error shows inline at the control that caused it, and the move is not kept | Edge cases |
| **Loading** | Results stay visible, in italic at 75% opacity, while a request is in flight (style guide pending state) | SC-001 |

**Alignment**: the main area is a 2×2 grid. Row 1 is the radar and the roster, row 2 is Per Category Ranking and H2H. Because the rows are shared, those two tables always start at the same height. Below 900px it collapses to one column in the order radar → ranking → roster → H2H.

**Session state**: `{settings, moves}` is kept in `sessionStorage` under `ffm.impact.v1`.
- Reads and writes are wrapped in try/catch.
- If storage is unavailable, the page still works; moves just don't survive a reload.

**Change markers**: before/after deltas, the radar's original outline and spoke segments, grayed
original distributions, and H2H result transitions are specified in
[003 contracts/ui.md](../../003-move-impact-diff/contracts/ui.md).
