# Is a player's next game just another draw from their past games?

A follow-up to the [weekly projection backtest](weekly-projection-backtest.md), for
[ccsv-rumble #33](https://github.com/dougkang/ccsv-rumble/issues/33). 2025-26 season.

## Answer

**For a single game, yes: nothing about it can be told apart from the player's previous games, for
any stat. For a week, mostly yes, with real exceptions in shot attempts, minutes and young or
low-minute players.** Counting missed games as zeros breaks the hypothesis most clearly.

"Can't be told apart" isn't the same as "identical". One game has little power to reveal a real
change (see [Power](#power)). Real changes do exist, but game-to-game noise is far larger than they
are. The last 15 games explain only 2% of how far a next game's points land from the season average.

## Results

The test assumes the games are interchangeable, so 5% of tests reject at the 5% level by design. The
question is how far above 5% the real rate goes. Rotation players (20+ minutes), compared with their
season so far:

| Stat | Next game | Next week, when playing | Next two weeks, when playing | Next week, missed games as zeros | Weeks not explained by noise (estimate) | Week-to-week carryover |
|---|---|---|---|---|---|---|
| Minutes (control) | 5.6% | 11.0% | 16.5% | 19.4% | 19% | 0.30 |
| FGA | 5.7% | 9.0% | 12.7% | 17.4% | 14% | 0.22 |
| 3PA | 5.4% | 8.0% | 11.0% | 14.9% | 9% | 0.20 |
| Points | 5.2% | 7.1% | 9.4% | 15.5% | 10% | 0.16 |
| Assists | 5.2% | 7.0% | 8.9% | 14.0% | 8% | 0.13 |
| FGM | 5.2% | 6.8% | 8.5% | 15.3% | 8% | 0.14 |
| Rebounds | 5.2% | 6.4% | 7.8% | 15.0% | 6% | 0.08 |
| FTM | 5.4% | 6.2% | 7.5% | 9.9% | 8% | 0.09 |
| FTA | 5.0% | 6.2% | 7.9% | 10.4% | 7% | 0.10 |
| 3PM | 5.2% | 5.8% | 7.3% | 10.8% | 5% | 0.08 |
| Turnovers | 5.3% | 5.8% | 7.1% | 10.8% | 4% | 0.05 |
| Blocks | 5.2% | 5.7% | 6.1% | 6.4% | 4% | 0.03 |
| Steals | 5.0% | 5.3% | 5.9% | 7.4% | 1% | 0.05 |

With each player's games shuffled, so the assumption is true by construction, the next-week test
rejects 4.3-5.1% of the time and carryover is about 0.00. That confirms the excess above is real, not
a flaw in the test. "Weeks not explained by noise" and carryover refer to next week when playing.

- **Attempts move more than makes.** FGA rejects at 9.0% against 6.8% for FGM, and 3PA at 8.0% against
  5.8% for 3PM. Shot volume follows role, while makes add shooting noise. FTA and FTM are about equal.
- **Steals and blocks are nearly pure noise**, even over two weeks.
- **Longer spans drift more.** Rejection rises from one game to one week to two weeks for every stat.
  Part of that is that more games make a real change easier to detect.
- **Missed games are the main break.** Counting them as zeros about doubles rejection, mostly in the
  low tail (points: 11.1% low, 4.4% high). This matches the backtest's finding on playing time.
- **No history length fits next game better.** Season so far, last 15, last 30 and two seasons all
  reject at 4.6-5.9%.

## Which players and situations

Next week when playing, rotation players (all players for minutes), averaged across stats. "Position"
is where the week landed in the player's distribution, and 0.5 means no shift. With games shuffled,
these groups reject about 4.4-5.3%, and their position stays within 0.484-0.511.

| Group | Rejected | Position | Reading |
|---|---|---|---|
| Under 15 minutes | 8.9% | 0.547 | Fails most, usually upward (FGA 13.6%) |
| 15-25 minutes | 7.3% | 0.514 | |
| 25-32 minutes | 6.4% | 0.485 | |
| 32+ minutes | 5.8% | 0.468 | Holds best, with a slight decline |
| First season in our data | 9.0% | 0.533 | Improving (FGA 15.2%, points 11.8%) |
| Veterans | 6.4% | 0.482 | |
| Under 10 points | 7.3% | 0.499 | |
| 10-15 points | 7.0% | 0.495 | |
| 15-20 points | 5.7% | 0.475 | |
| 20-25 points | 6.3% | 0.465 | |
| 25+ points | 5.2% | 0.465 | Rarely rejects, but points run low (0.425) |
| 40+ prior games | 7.4% | 0.487 | More time to drift (FGA 11.0%, 3PA 10.4%) |
| Under 40 prior games | 6.0-6.1% | 0.486 | |
| Final four weeks | 7.5% | 0.489 | Attempts move (3PA 11.8%, FGA 11.0%) |
| Oct-Nov, Dec-mid Mar | 6.3-6.4% | 0.485-0.495 | |
| C / G / F | 7.1% / 6.9% / 6.7% | 0.482-0.498 | Position barely matters |
| G,F / F,C | 6.0% / 5.2% | 0.473-0.489 | |

Situations, for the next game. Rejection stays near 5%, but the average shift shows the effect:

| Situation | Points position | FGA position | Rejected |
|---|---|---|---|
| The club's top-usage teammate is out | 0.556 | 0.585 | 5.7% |
| That teammate is playing | 0.477 | 0.472 | 5.1% |
| Back after 7+ days out | 0.428 | 0.427 | 5.1% |
| First 5 games on a new team (122 games) | 0.466 | 0.434 | 5.3% |
| Back-to-back | 0.510 | 0.516 | 5.7% |
| Home / away | 0.500 / 0.492 | 0.495 / 0.503 | 5.3% / 5.2% |

## Individual players

Over a full season, each player-stat pair has much more power. Of 214 rotation players, 21% have
points that depart from their own distribution at the 5% level, against 5% expected. After correcting
for testing this many pairs, 25 players (12%) have at least one stat that clearly changed, and 189
have none. FGA is the most common at 5.1% of players, and steals and blocks have none.

The clearest cases are role changes:

| Player | Stat | First third of season | Last third |
|---|---|---|---|
| Nique Clifford | Points | 4.7 | 12.8 |
| Ace Bailey | FGA | 9.1 | 16.2 |
| Isaiah Collier | FGA | 5.7 | 12.9 |
| Cooper Flagg | FGA | 14.0 | 19.0 |
| Miles Bridges | FGA | 17.2 | 11.2 |
| Donovan Mitchell | 3PA | 10.4 | 6.9 |

## The predicted week against the distribution

Where does each model's per-game line for the next week fall among averages of the same number of
the player's past games? (Rotation players, per game.)

| Stat | xlift line significant | xlift shift that carries through | xlift error | Season average error | ESPN line significant | ESPN shift that carries through | ESPN error |
|---|---|---|---|---|---|---|---|
| Points | 0.1% | 0.93 | 3.57 | 3.64 | 3.6% | 0.12 | 4.23 |
| Rebounds | 0.0% | 1.01 | 1.34 | 1.36 | 2.9% | 0.26 | 1.49 |
| Assists | 0.1% | 0.86 | 1.05 | 1.07 | 4.5% | 0.19 | 1.23 |
| Steals | 0.0% | 1.08 | 0.50 | 0.52 | 0.6% | 0.45 | 0.53 |
| Blocks | 0.5% | 1.35 | 0.37 | 0.38 | 2.2% | 0.38 | 0.40 |
| 3PM | 5.7% | 1.07 | 0.68 | 0.70 | 5.0% | 0.18 | 0.77 |
| Turnovers | 0.1% | 1.07 | 0.65 | 0.67 | 1.2% | 0.30 | 0.72 |
| FGM | 0.1% | 0.99 | 1.35 | 1.37 | 2.8% | 0.13 | 1.57 |
| FGA | 0.3% | 0.82 | 2.23 | 2.25 | 7.7% | 0.04 | 2.79 |
| FTM | 0.1% | 0.82 | 1.09 | 1.12 | 2.9% | 0.23 | 1.26 |
| FTA | 0.0% | 0.81 | 1.30 | 1.33 | 3.1% | 0.22 | 1.51 |

- **xlift's prediction is almost never significantly different from the player's own distribution**,
  yet its small shifts are real. A point of shift from the season average brings about a point of
  actual change. That beats the season average on every stat, but only by 1-3%.
- **xlift's 3PM rate is an artifact.** Those are non-shooters averaging about 0.004 threes, whose line
  gets pulled slightly above nearly all-zero games, and 96% of them then make none.
- **ESPN's line stands out more but means less.** Only 4-45% of its shift from the season average
  carries through, and it has a larger error than the plain season average on all 11 stats.

## Power

How often the test rejects when a real change exists, for a rotation player with 40 prior games:

| Real shift in the stat | Next game: points | Next game: FGA | 3-game week: points | 3-game week: FGA | 3-game week: minutes |
|---|---|---|---|---|---|
| None (runs a little under 5%) | 2.5% | 4.3% | 3.5% | 3.0% | 3.5% |
| 10% | 5.5% | 6.2% | 8.5% | 11.5% | 18.5% |
| 25% | 8.7% | 9.5% | 14.7% | 22.0% | 57.0% |
| 50% | 19.8% | 25.0% | 40.3% | 55.5% | 82.8% |

So a next game rarely flags even a 50% change. This is why the single-game result says more about
how noisy a game is than about players staying constant. Recent form confirms it. The last 15 games'
departure from the season average carries over about 57% for points, 69% for FGA and 12% for steals,
but explains only 1.9%, 3.4% and 0.1% of the next game's departure. Over three games, it explains
4.0%, 6.3% and 0.1%.

## What this means

- **Don't react to one game or one week** for most players, and especially not on steals and blocks.
- **Season average is a strong baseline for per-game rate.** xlift's recency adds a small, real gain.
- **Watch role signals instead:** FGA and minutes trends, a top-usage teammate being out, players in
  their first season and those under 25 minutes.
- **Availability is the bigger question for a week**, as the backtest also found.

## Method and limits

- **Next game:** the game's rank among the player's previous games, needing at least 10 in the
  season. If the games are interchangeable this rank is exactly uniform for any distribution, with
  ties split at random, which matters for low-count stats like blocks.
- **Week:** a permutation test of the week's total against random same-sized subsets of all the
  player's games so far plus that week. Weeks start on Mondays, skip the All-Star week, and need a
  game in the past 14 days. "When playing" fixes the games played. The zeros version fills in missed
  club games, with counts that are approximate after a trade.
- **Percentages:** FG% and FT% are tested as makes and attempts, as requested.
- **Uncertainty:** the per-stat tests are not independent, so intervals resample whole players. For
  example, next-game points rejects at 5.2% (4.8-5.6%) and next-week FGA at 9.0% (8.1-9.9%). Rows in
  the group tables aren't corrected for multiple comparisons, so small differences there may be noise.
- **Estimates:** "weeks not explained by noise" uses Storey's estimate, from how many p-values sit
  above 0.5.
- **Scope:** this is one season. Grouping players by their own average can shift the results by
  selection alone, and the shuffled run measures that: top scorers reach 0.484 there against 0.465 for
  real, and under-15-minute players 0.511 against 0.547.

## Run it

Set up the database copy as in the [backtest](weekly-projection-backtest.md#run-it), then:

```bash
cd analysis && uv run python distribution_test.py
```
