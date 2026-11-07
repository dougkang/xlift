# T-test backtest: is next week statistically different from the past X games?

For [ccsv-rumble #33](https://github.com/dougkang/ccsv-rumble/issues/33), 2025-26 season, rotation
players (20+ minutes). Every Monday, each player's games in the coming week are t-tested, per stat,
against a distribution built from the games before that Monday. FG% and FT% are tested as makes and
attempts. The week is the games actually played, so this tests the per-game distribution.
Availability is covered in the [weekly backtest](weekly-projection-backtest.md).

## Answer

**Yes, the hypothesis mostly holds. For about 94% of player-week-stats, next week is not
significantly different from the past games, and only 1-1.5 points of the rest go beyond what
chance produces. A recency-weighted distribution does better than equal weights, both by this
test and on error. A half-life of 10 games gives the most accurate mean.**

| Distribution | Significant at 5% | When the games are shuffled | Excess | Error per game: points | Error per game: FGA |
|---|---|---|---|---|---|
| Last 5 games | 6.6% | 6.1% | +0.4 | 3.97 | 2.37 |
| Last 10 | 6.4% | 5.5% | +0.9 | 3.67 | 2.23 |
| Last 15 | 6.3% | 5.2% | +1.0 | 3.61 | 2.21 |
| Last 30 | 6.2% | 5.2% | +1.1 | 3.62 | 2.25 |
| Season so far | 6.5% | 5.0% | +1.5 | 3.64 | 2.25 |
| Last 82 (two seasons) | 7.7% | 6.1% | +1.6 | 3.85 | 2.48 |
| Weighted, half-life 5 games | 5.5% | 4.9% | +0.6 | 3.58 | 2.16 |
| **Weighted, half-life 10** | 5.8% | 4.9% | +0.9 | **3.53** | **2.16** |
| Weighted, half-life 20 | 5.9% | 4.8% | +1.1 | 3.55 | 2.20 |
| Weighted, half-life 40 (xlift's weights) | 6.1% | 4.9% | +1.2 | 3.58 | 2.23 |
| xlift's shipped projection (shrunk) | 6.2% | not run | | 3.57 | 2.23 |

Next week, all 12 stats pooled, 4,041 player-weeks.

- **Excess** is the real rate minus the rate when each player's games are shuffled, which makes the
  null true by construction. The counts aren't normal and the samples are small, so the shuffled
  rate is the honest baseline instead of 5%. It sits near 5% for every distribution except the
  shortest and longest.
- **Weighting toward recent games helps.** Half-lives of 5 to 10 games have the fewest significant
  weeks and the smallest errors. Weighted 82-game distributions beat equal-weight windows of any
  length, because they react to role changes without discarding older games.
- **xlift's half-life of 40 is longer than ideal for next week.** It was fit to the next 15-60 games.
  For next week, a half-life of 10 cuts points error by 1.4% against xlift's weights, and by 2.9%
  against the season average.
- **Few games mean little power.** With 2-4 games in a week, only a large shift can reach
  significance, so "not significant" is weak evidence by itself. The error columns are the practical
  measure: a typical miss is still about 3.5 points per game.

## By stat

Next week, significant at 5% (excess over shuffled):

| Distribution | Points | Rebounds | Assists | Steals | Blocks | 3PM | 3PA | Turnovers | FGM | FGA | FTM | FTA |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Season so far | 7.4% (+2.6) | 6.3% (+1.0) | 6.8% (+1.8) | 4.9% (-0.2) | 6.6% (+0.6) | 5.8% (+0.9) | 7.6% (+2.8) | 5.2% (+0.9) | 7.0% (+2.9) | 9.0% (+4.0) | 5.5% (0.0) | 5.5% (+0.1) |
| Weighted, half-life 10 | 6.1% (+1.7) | 5.8% (+0.9) | 5.6% (+0.5) | 5.1% (0.0) | 6.4% (+0.4) | 5.0% (+0.3) | 6.3% (+1.8) | 5.0% (+0.6) | 5.6% (+1.3) | 7.9% (+3.0) | 5.2% (-0.2) | 5.0% (0.0) |
| xlift's weights (40) | 6.5% (+1.7) | 5.9% (+0.9) | 5.9% (+1.0) | 4.6% (-0.4) | 6.2% (+0.7) | 5.5% (+0.8) | 7.2% (+2.5) | 5.1% (+0.9) | 6.4% (+2.4) | 8.7% (+4.0) | 5.5% (0.0) | 5.6% (+0.4) |

- **Shot attempts break most.** FGA and 3PA have the largest excess for every distribution. Attempts
  follow role, and roles change. FGM and points follow from attempts.
- **Steals, free throws and blocks hold.** Their weeks are indistinguishable from the past games
  under any distribution.

## Who it holds for

Next week, excess over shuffled:

| Group | Season so far | Last 15 | Half-life 10 | xlift's weights |
|---|---|---|---|---|
| First season in our data | +4.9 | +2.8 | +3.6 | +4.3 |
| Veterans | +1.1 | +0.9 | +0.6 | +0.9 |
| 15-25 minutes | +2.1 | +1.2 | +1.0 | +1.8 |
| 25-32 minutes | +1.5 | +1.0 | +1.0 | +1.3 |
| 32+ minutes | +0.6 | +0.9 | +0.4 | +0.4 |
| 25+ points | -0.9 | 0.0 | -0.5 | -0.3 |

The hypothesis holds best for stars and heavy-minute veterans. It fails most for young players,
whose production drifts upward through the season, and a short half-life helps them most.

## Two weeks out

With weeks +1 and +2 together, excess grows for every distribution, because more games give more
power and more time to drift. Season so far reaches +2.8 points and xlift's weights +2.5. A half-life
of 5 stays lowest at +1.1, and a half-life of 10 at +1.5 has the smallest error (points 2.81 against
2.93 for the season average).

## Recommendation

Shorten xlift's recency half-life for weekly use, to about 10 games, or fit it to a next-week target.
It's a small gain, about 1-3% on error. Steals, blocks and free throws can stay on any distribution.

## Method

- **Test:** for each player-week and stat, t = (week mean − distribution mean) / (sd × √(1/n + 1/g)),
  with df = n − 1. Here n is the past games' count (Kish's effective n when weighted) and g the week's
  games. The week's spread is taken from the past games, so one-game weeks can be tested.
- **Welch's test**, with the week's own spread, was also run for weeks of 2+ games. It's badly
  miscalibrated here: it rejects 8-14% even with the games shuffled, because 2-4 games give a poor
  variance estimate. It's in `analysis/output/ttest_summary.md` but not used for conclusions.
- **Weighted:** game j games ago weighs 0.5^(j / half-life) over up to 82 games, and a 2024-25 game
  also weighs 0.25, as in xlift. The distribution uses the weighted mean and unbiased weighted variance.
- **xlift's shipped projection** uses `build_projections`' mean and covariance. Its shuffled baseline
  wasn't run, because it would mean refitting the model on shuffled data, but its weights match the
  half-life-40 row, whose baseline is 4.9%.
- **Pool:** weeks start on Mondays, skip the All-Star week, and need 10+ games this season and a game
  in the past 14 days.

## Run it

Set up the database copy as in the [weekly backtest](weekly-projection-backtest.md#run-it), then:

```bash
cd analysis && uv run python ttest_backtest.py
```
