# Project Overview

Goal of this repo is to create a collection of decision-making aids for Fantasy Basketball.

## A Primer in Fantasy Basketball

A team represents the primary unit of comparison.
Each team consists of a fixed number of players.
There are multiple scoring strategies, but for now, we consider 9 category head 2 head (9cat h2h).
In this scoring strategy, each player has 9 separate stat categories that they contribute to (9cat).
Each week they face one team where they accumulate points in these categories.
A team that scores better in a given category will win that category.

How a week's matchup counts in the standings depends on the league:

- **H2H Each Category**: every category is its own W, L or T in the standings, so a week
  counts as something like 6–3–0. **Our league scores this way.**
- **H2H Most Categories**: whoever wins more of the 9 categories gets one W for the week.

The scoring format declares which rule applies (`9cat_h2h_each` or `9cat_h2h`), and the tools
report records accordingly. Under each-category scoring, the record to maximize is the expected
number of categories won, with a tie counting half: a 5–4 week is middling, not a win. Every
category counts the same, so punting a category costs a full W every week.

A player's contributions to each category can be fit to a normal distribution.
Barring any changes, we assume that future contributions in that category will come from this distribution.

A team's scoring can then be an aggregation of these scores.  Adding/removing players affects this aggregation.

### Gotchas in Aggregate Scoring

In 9cat h2h, there are 3 exceptional stat categories: Field Goal % (FG%), Free Throw % (FT%) and Turnovers (TO).

Percentage-based stats should be treated differently, since the statistic is not additive.
Instead, the statistics that contribute to that percentage statistic must be added individually.  The percentage
conversion should then be done at the team level.

Turnovers are another class of stats that can be called a negative stat.  In this case, less is better.

## Style Guide

See [Style Guide](style.md) for more information about style.

## Tools

1. [Impact Analysis](tool1-impact-analysis.md) - Visualize tactical and strategic impacts of adding/dropping players
2. [Player Analysis](tool2-player-comparison.md) - Identify potential players with the unique ability to subvert correlated stats
3. And more
