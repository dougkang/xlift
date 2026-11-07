# Weekly dAB backtest: adding "right now" to dAB

A follow-up to the [weekly projection backtest](https://github.com/dougkang/xlift/pull/17)
([ccsv-rumble #33](https://github.com/dougkang/ccsv-rumble/issues/33)). That backtest found that
availability, not the per-game line, is the largest source of weekly error, and that zeroing
anyone who missed all of last week's games helps more than any change to the line. dAB had no
way to see that: its "recent" term is the last 15 games played, which looks the same for a
player who sat out last week and one who missed scattered games a month ago.

## Answer

**Add a recency-weighted "right now" term to dAB: the share of the player's last 20 team games
played, the latest weighted 1 and each earlier one half as much (a half-life of one game).**
It cuts dAB's error by about a fifth on its own 15-game target and by a third on next week,
in every season. It also fixes dAB's optimism: shipped dAB overestimates next-15 availability by
5.5 points on average, and by 18 points for players who missed the previous week.

17,399 player-Mondays in 2023-24, 2024-25 and 2025-26 (2,935 of them out all of the week
before), each model scored leave-one-season-out:

| Model | Next 15 games: MSE | vs shipped | bias | Next week: MSE | vs shipped | bias (games/wk) |
|---|---|---|---|---|---|---|
| Shipped dAB | 0.0762 | | +0.055 | 0.1090 | | +0.19 |
| Zero if out last week, else dAB | 0.0895 | -17% | -0.031 | 0.0920 | +16% | -0.11 |
| dAB refit | 0.0744 | +2% | +0.036 | 0.1062 | +3% | +0.15 |
| + last week's share played | 0.0651 | +15% | +0.026 | 0.0799 | +27% | +0.10 |
| + out-all-last-week flag | 0.0668 | +12% | -0.015 | 0.0869 | +20% | -0.12 |
| **+ right now, half-life 1 game** | **0.0616** | **+19%** | +0.020 | **0.0723** | **+34%** | +0.06 |
| + right now, half-life 2 | 0.0621 | +19% | +0.016 | 0.0753 | +31% | +0.04 |
| + right now, half-life 5 | 0.0650 | +15% | +0.011 | 0.0852 | +22% | +0.03 |

- **The zero rule is too blunt for dAB.** It helps next week but hurts over 15 games, because most
  players who sat out a week come back within the next 15. The fitted term moves them down by
  the right amount instead.
- **The shortest half-life wins.** Whether a player played his team's last game or two says the
  most. It beats "last week's share" because it doesn't depend on how many games fell in last
  week, and it ranks first in every season for both targets.
- **The 15-game window nearly drops out.** Once "right now" is in, its weight falls from 0.54 to
  0.04, and the three-season rate's rises from 0.12 to 0.24.

## The new dAB

    dAB = clip(ā + B3·(right now − ā) + B1·(last 15 − ā) + B2·(long run − ā), 0, 1)

with ā = 0.716, B3 = 0.4271, B1 = 0.0377, B2 = 0.2356, fit to the next 15 team games. δ = 0.05,
κ = 5 and κ_w = 0 stay as the availability report fit them.

The weights are fit to the next 15 games, dAB's original target, rather than next week. Fit to
next week, the right-now weight is 0.69 instead of 0.43, which is better for start/sit but
penalizes an injured player's value for the rest of the season, which matters for trades and
pickups.

ā drops from 0.770 to 0.716 because this pool is every Monday, including players who are hurt,
where the availability report sampled a few cutoffs a season. The new ā is the rate the weights
were fit around.

## Limits

- **Tags double count somewhat.** dAB × tag multiplies by the injury tag, and a tagged player
  usually has also missed his last games, which dAB now sees. The tag multipliers are still
  judgment, not fit; they may want lowering toward 1.
- **The pool is the availability report's:** 10+ games and 20+ minutes a game before the cutoff.
- **Per player, not per team.** The effect on xLift and category wins wasn't backtested.

## Run it

```bash
cd analysis && uv run python weekly_availability.py
```

Writes `analysis/output/weekly_availability.md`, with per-season tables, results for players out
and in last week, and every candidate's coefficients.
