# Tool 1: Impact Analysis

See [Project Overview](overview.md) for a primer on fantasy basketball and an overview of the tools we are trying to build.

The general idea of this tool is to provide a tool that visualizes the impact of adding/dropping players tactically and
strategically. We accomplish this by doing a Monte Carlo simulation based on player's stat distributions over
the past X games, where X may be specified by the user.

## The Comparison

Teams should be compared in two ways: tactically (short-term) and strategically (long-term).

### Tactial:

Against the current matchup - the user may want to tactically stream picks in to try to win the matchup.
Here, the number of games becomes important.  In 9cat h2h A player who is slightly worse, but plays two games
might be more useful than a better player who only plays one.  The final comparison should be done against
the current matchup and aggregate based on number of games.

### Strategic:

Users may also be looking long-term.  Swapping players is ultimately a game of tradeoffs: a player that is
good in certain areas may be poor in others.  As such, it is a common strategy to punt certain stats in favor
of others.

When looking strategically, the number of games matters less, since we are looking at a longer time window
where players' games played average out.  Another factor, however, becomes important, which is injury-proneness.
A player's tendency to become injured and not play impacts the bottom line.

The final comparison should be done against all teams.  A team that can reliably win against all teams in 5 categories
is a great team.

## The UI

The UI should consist of two primary sections: the simulation visualization and the player picker sidebar.

### Simulation Visualizer

The simulation visualization should show the result of the Monte Carlo simulation across all teams.

It should prominently show the team name, manager and projected W-L score.
In strategic mode, an overall W-L score is computed by matching the selected team against each other team and
counts the overall matchup wins and losses. In tactical mode, the W-L score is computed only looking at the current
matchup for the selected team.

Below this, we should have two columns:

On the right, we should have a radar visualization where each axis represents a team's rank in a particular category
It should highlight the selected team's radar, with other team(s) (singular if in tactical mode) overlaid with muted
transparency/colors. Below the radar, in strategic mode, we should provide the ranking of the selected team for each
category.  In tactical mode, we should report the difference between averages for each category.

On the left, we should have the roster.  A dropdown should allow the user to select different teams. A '-' button to the
left of each player should drop said player when pressed.  Dropping a player puts the player in the list of free agents.

Below it all, we should have a detailed category breakdown, which shows a distribution curve for each category for the
selected team. In strategic mode, the league leader and league average in that category should be overlaid. In tactical
mode, only the opponent's distribution should be overlaid. In both cases, it should highlight the selected team's radar,
with other distributions overlaid with muted transparency/colors.

### Player Picker 

On the right sidebar, we should list out all players not on selected team.
A search bar should be present at the top enable name-based filtering.
A '+' button to the left of each player should add the player to the selected team iff the roster has an empty slot.

If the player is a free agent, we simply add the player and run the simulation.
If the player is on another team, we must select a player on the roster or a free agent in the list to swap with.

The simulation should then update to reflect the change.

### Other UI Elements

We need to decide where to put additional UI elements, which are listed as follows:

- Impact Analysis header + explanation of tool
- Reset to default button to move players back to their original teams or the free agent list
- Tactical/Strategic modes, which affects the W-L calculations

## Next Steps after Initial Implementation

- When fitting to a normal distriution, we have an error metric.  This error should be propagated up to the aggregation.
- Pick different distribution windows, such as time windows.
- Consider past seasons' stats with decreasing weight
