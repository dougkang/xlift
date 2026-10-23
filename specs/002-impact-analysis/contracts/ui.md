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
| **Controls** | Changing any control re-runs the analysis. Tactical-only controls (opponent, period) appear only in tactical mode. The window field is debounced by 250 ms | FR-001–FR-004, FR-025 |
| **Reset** | Clears the move list. Disabled when there are no moves | FR-023 |
| **Data line** | Shows `freshness` | FR-005 |
| **Record headline** | A subheader spanning both the main area and the sidebar, with a 1px rule below. Left: the team name (large) with the manager as a subtitle. Right-aligned: the record (large) with its units label below. Team, manager and record, with a units label ("vs 17 teams" or "categories vs <opponent>"). Tactical adds the matchup win %. Shows "Choose an opponent" when `OPPONENT_REQUIRED` | FR-014 |
| **Roster** | Right-hand column (swapped with the radar per user preference, 2026-10-23). Player names in bold. One row per player of the selected team, with "−" (destructive style) on every row. Shows slot, status, NBA team, and `games_remaining` in tactical mode. A short history gets an asterisk. Rows changed by moves are marked in the yellow "yours" color | FR-018, FR-019 |
| **H2H** (section) | Below the roster and its footnotes. One row per opponent: name (bold) with the manager, projected category W–L–T (column "H2H"), win %, and the result (W/L/T, by the more-than-half rule). A footer row totals the categories W–L–T and the matchups W–L–T; the matchup total equals the headline record. All values come from the API (`matchups[].category_record`, `matchups[].result`, `matchup_totals`) | FR-014 |
| **Radar** | D3, centered in the left column with the category table below it. One axis per category. The selected team is primary with a light primary fill. Other teams use muted secondary shades with a light secondary fill (`#F5C1A9`, 12%), and the opponent is secondary `#A96043`. Hovering an axis shows the selected team's rank | FR-015 |
| **Category table** | Strategic (sub-header "Per Category Ranking", below the radar): category label (bold, unlabeled column), Rank, Avg, League (league average), Leader (team), then the leader average (unlabeled column). Tactical: selected average, opponent average, and difference with a favors marker. Ratios show 3 decimals as `.473` | FR-016 |
| **Category breakdown** | Plot. One small density chart per category. Fills use the lighter palette shade, and each curve has a vertical average line: solid for teams, dotted for league-related curves. Each line is labeled with its role and value (e.g. `You .471`, `League .465`). Labels sit in a single row above the plot. A label moves down to another row only when it would collide with one already placed. The legend names the leader, next best, league average or opponent | FR-017 |
| **Player picker** | Search box plus a paged list (50 per page). Each row shows `+`, name, NBA team, owner (or FA), status, games remaining (tactical), and an asterisk. `+` is disabled when `can_add` is false and no swap option exists, with `add_blocked_reason` as its title. For a rostered player, `+` opens the swap dialog | FR-020, FR-021, FR-026, FR-027 |
| **Swap dialog** | "Give <team> one of:" followed by the selected team's roster (when `roster` is allowed) and a free-agent search (when `free_agent` is allowed). Confirming appends a `swap` move | FR-021 |
| **Footnotes** | Every `footnotes` entry, directly below the roster table | FR-007 |
| **Errors** | A 422 move error shows inline at the control that caused it, and the move is not kept | Edge cases |
| **Loading** | Results stay visible, in italic at 75% opacity, while a request is in flight (style guide pending state) | SC-001 |

**Session state**: `{settings, moves}` is kept in `sessionStorage` under `ffm.impact.v1`.
- Reads and writes are wrapped in try/catch.
- If storage is unavailable, the page still works; moves just don't survive a reload.
