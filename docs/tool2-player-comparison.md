# Tool 2: Player Analysis

See [Project Overview](overview.md) for a primer on fantasy basketball and an overview of the tools we are trying to build.

The general idea of this tool is to provide a tool that visualizes the impact of adding/dropping players tactically and
strategically. We accomplish this by doing a Monte Carlo simulation based on player's stat distributions over
the past X games, where X may be specified by the user.

## xLift leaderboard

The first view ranks players by **xLift** (see [Impact Analysis](tool1-impact-analysis.md#xlift)):
the expected extra category wins per week, over every opponent, a player is worth to a team. It
uses the same numbers as Impact Analysis's player picker.

Each player is one row: a bar split into the categories the value comes from. A segment right of
zero adds wins in that category; one left of zero costs wins (a high-volume, low-percentage
shooter often costs FG%). The black tick marks the net, which is also the number beside the name.

- **Evaluate for**: a team, or **League**. A team scores each player for that team, replacing its
  weakest active player (or filling an open slot); it's also the team Impact Analysis opens.
  **League** scores each player for every team but their own, each with its own weakest player,
  and averages: a value that doesn't depend on any one team's position.
- **Pool**: a dropdown of free agents, all players (adding players on other teams, as trade
  targets), or one team's players. For a team, its own players are listed too (highlighted yellow):
  in All players, and beside any other team's players for comparison, so the team itself isn't a
  Pool choice. They're valued against its weakest active player, as Impact Analysis values a
  roster (the weakest shows 0); everyone else as if they replaced that weakest player.
- **Show top**: 10 to 50 players. **Min games**: hides projections built on fewer games.
- The window and the Fragility Penalty are shared with Impact Analysis, as are the league and
  team: switching tools keeps them.
- The leaderboard always uses rosters as they are. Moves made in Impact Analysis don't apply.

### Trades

Below the leaderboard, **Trades** suggests one trade with every other team. Teams need different
things: a team that loses rebounds by a hair gains more from a rebounder than a team that already
wins them, and the other way around for shooters. So a 1-for-1 trade can raise **both** teams'
expected weekly category wins at once.

For the selected team and each other team, every swap of one active player for one active player
is scored for both teams with xLift's measure (the change in expected weekly category wins against
the whole league, with both rosters changed). Of the swaps that help both teams, the one shown is
the fairest: the one whose smaller gain is as large as possible. Each row shows what you give and
get, each team's gain, and then your gain in each category, one column each, gains in bold. Teams with no swap that
helps both say so. **View Impact** opens Impact Analysis with just that trade as your move.
