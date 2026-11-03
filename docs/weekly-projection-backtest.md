# Weekly projection backtest, 2025-26

How well does ccsv-rumble's projection predict each player's next week and next two weeks?
([ccsv-rumble #33](https://github.com/dougkang/ccsv-rumble/issues/33))

## Answer

**Keep the idea of multiplying a line by the club's games, but replace ESPN's line with xlift's and
zero out anyone who missed all of last week's games.** Availability, not the per-game line, is the
largest source of error, and ESPN's line is also the weakest one we tested once a few games exist.

Next week, among the top 180 fantasy players, averaged over 23 Mondays:

| Model | Value rank correlation | Typical error, relative to spread (lower is better) | Games overprojected per week |
|---|---|---|---|
| ESPN × every club game | 0.24 | 0.81 | +1.00 |
| ESPN, zero if out last week | 0.58 | 0.60 | +0.37 |
| Season average, zero if out last week | 0.61 | 0.59 | +0.37 |
| **xlift, zero if out last week** | **0.62** | **0.56** | +0.37 |
| xlift, zero if out, × availability | 0.62 | 0.54 | -0.11 |

The live approach sits between the first two rows. It drops players in the league's IL slots but
counts everyone else as playing every game. IL history for 2025-26 isn't kept, so "out last week"
stands in for it.

xlift with the zero rule beat ESPN with the zero rule on value rank in 23 of 23 weeks. The order of
the models is the same in the top 250.

## What drives the error

- **Volume matters most.** Assuming every club game overprojects by a full game a week. That leaves
  a typical player's week about 17 points too high. The zero rule more than doubles value rank (0.24
  to 0.58) with no change to the line.
- **The line matters less, but ESPN's is the weakest current one.** Per-game points error when
  playing is 4.29 for ESPN, 3.83 for the season average and 3.74 for xlift. ESPN's error grows from
  4.05 early to 4.36 by the end, because it doesn't update.
- **ESPN has no early-season edge on points.** In weeks 2-6, its per-game points error is 4.05
  against 3.89 for the season average and 3.76 for xlift. It does rank players better than the
  season average then (0.59 vs 0.55), but not better than xlift (0.61).
- **ESPN misses useful players.** About 28 of each week's real top 180 have no ESPN line (median 27,
  range 20-50). Every model here is scored only on players ESPN projects, so this gap is on top of
  the numbers above.
- **FG% and FT% are about equally hard for everyone.** Rank correlation is about 0.38 and 0.36 for
  the best models, and the line choice barely moves them.

## Week +1 vs week +2

Value rank on the top 180:

| Model | Week +1 | Week +2 alone | Weeks +1-2 total |
|---|---|---|---|
| ESPN × every club game | 0.24 | 0.23 | 0.24 |
| ESPN, zero if out last week | 0.58 | 0.48 | 0.56 |
| xlift, zero if out last week | 0.62 | 0.52 | 0.61 |
| xlift, zero if out, × availability | 0.62 | 0.53 | 0.62 |

Accuracy falls about 0.1 by the second week, as injuries heal or new ones appear. The order of the
models doesn't change, and the plain ESPN line stays flat because it has no recent information to
lose.

## Is the ESPN test fair?

Yes, as far as I can tell. The 2025-26 set ESPN still serves looks like a preseason snapshot, with
no sign of having seen the results (`analysis/espn_leak_check.py`, 303 players):

- Its points-per-game error is 2.59, barely better than last season's average at 2.73. Its changes
  from last season correlate only 0.33 with what actually changed.
- It tracks a player's first, middle and last third of games about equally (0.34, 0.31, 0.35). A set
  revised during the season would lean toward later games.
- It doesn't know about in-season injuries: Giannis is projected for 71 games and played 36, Anthony
  Davis 64 and 20, Keegan Murray 77 and 23.
- It missed the breakouts: Alexander-Walker is at 9.3 points against 20.8 actual, Duren at 12.7
  against 19.5. Ryan Rollins (17.3) and Cedric Coward (13.6) have no line at all.

ESPN does revise some lines during a season. 14 of the 171 rostered 2026-27 lines changed between
the October 22 capture and November 2, most of them trivially, but Ajay Mitchell went from 12.2 to
15.9 points. So a few 2025-26 lines may include early revisions, which could only flatter ESPN, and
ESPN still loses. It also means re-capturing ESPN weekly could do somewhat better than this frozen
line, which I can't test without past captures. The current `data/projections.csv` hasn't changed
since October 22, so the frozen line is what the live pipeline has been using.

## Method

- **Season and weeks:** every Monday from October 27, 2025 to April 6, 2026, using only earlier games.
  Targets are real Mon-Sun totals, including zeros for players who didn't play. Windows touching the
  All-Star week (February 16-22) are dropped.
- **Players:** those ESPN projects, ranked each Monday by the average of their ESPN and xlift value
  ranks, so no model picks a pool that flatters it. Cut at 180 and 250.
- **Scoring:** rank correlation within each week and error on totals, per category and as a combined
  value. FG% and FT% are scored as impact (makes minus the league rate × attempts).
- **xlift:** the shipped `build_projections`, run as of each Sunday, with 2024-25 logs loaded so it
  has the prior season it would have in production.

## Limits

- This is one season, and the IL rule is a stand-in, as noted above.
- The zero rule ignores Yahoo's injury tags, which could do better since they update before games.
- The optional team-level check in the plan (does this pick category winners?) wasn't run. These
  results are per player.

## Run it

```bash
cp data/ffmodel.sqlite /tmp/backtest.sqlite
export FFMODEL_DB_URL=sqlite:////tmp/backtest.sqlite
(cd backend && uv run ffm load nba --season 2024-25)
(cd analysis && uv run python weekly_backtest.py)
```

Output, including ESPN's data, goes to `analysis/output/`, which git ignores.
