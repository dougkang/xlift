# Project Overview

Goal of this repo is to create a collection of decision-making aids for Fantasy Basketball.

## A Primer in Fantasy Basketball

A team represents the primary unit of comparison.
Each team consists of a fixed number of players.
There are multiple scoring strategies, but for now, we consider 9 category head 2 head (9cat h2h).
In this scoring strategy, each player has 9 separate stat categories that they contribute to (9cat).
Each week they face one team where they accumulate points in these categories.
A team that scores better in a given category will win that category.
A matchup's winner is determined by who has more wins across the 9 categories.

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
2. Player Potential - Identify potential players with the unique ability to subvert correlated stats
3. And more
