# Tool 1: Impact Analysis

See [Project Overview](overview.md) for a primer on fantasy basketball and an overview of the tools we are trying to build.

The general idea of this tool is to provide a tool that visualizes the impact of adding/dropping players tactically and
strategically. We accomplish this by doing a Monte Carlo simulation based on player's stat distributions over
up to the past X games, where X may be specified by the user (default 82).

Only regular-season games are considered. Play-in, playoff, preseason, and All-Star games are
never part of any calculation. The X games span season boundaries when needed: if the current season has fewer than
X games, earlier seasons fill the rest. A player with fewer than X games in total (e.g. a rookie)
is still simulated on the games available, but is marked with an asterisk wherever they appear,
with a footnote stating how many games the distribution is based on (e.g. "* 3 of 82 games").

Recent games count more. Each game's weight halves every 40 games back, and falls to a quarter
for each season it is older, so last night counts most and a game from two seasons ago counts
little. This keeps a long, steady history while still following a real change in role.

Part of any player's record is luck, so each player's per-game averages are pulled toward a
typical player's before simulating, more strongly the noisier they are: hard for a rookie with
two games, barely for an established veteran. Counting stats are pulled according to the
player's own sampling error. FG% and FT% are pulled toward the league rate according to the
player's attempts, so a hot streak on few free throws counts for little. Blocks are not pulled:
a center's block rate is skill, not noise.

How often a player is expected to play is set by the **Fragility Penalty**, and it applies to
the whole analysis: the strategic simulation's games and every xLift value.

- **dAB × tag** (the default): dAB, scaled down for a current injury tag (IL 0.3, O 0.6,
  Q/GTD/DTD 0.9, SUSP 0.7, NA 0).
- **dAB** (Decay-weighted Availability Blend): games played over games available, blending the
  last 15 games with the last three seasons. Older seasons count far less (a twentieth per
  season of age), so an old injury is mostly forgiven, and a whole missed season counts as
  missed games once the player is back. Both rates are pulled toward the league's typical rate
  when there is little evidence. Its parameters are fixed from a backtest and not shown.
- **Last 15**: games played over the most recent 15 games, whatever X is.
- **None**: no penalty. Every player plays every game, except players in an IL slot, who play
  none, on any team.

In tactical mode the matchup uses each player's games remaining, so the Fragility Penalty only
changes xLift there.

## xLift

Every player shows **xLift** (expected lift): how many more category wins
per week, summed over every opponent in the league, the player is worth to a team. A team's
expected wins in a category against an opponent is the chance its weekly total beats theirs,
given how much weekly totals vary; FG% and FT% are recomputed from makes and attempts.

The baseline is the team's **weakest active player**: the one whose removal costs the fewest
expected wins (an empty active slot, or a player with no games, counts as weakest).

- A **free agent** or another team's player is scored as replacing that weakest player (or
  filling an open slot), for the selected team.
- A **roster player** is scored against a second copy of the weakest player, so the weakest
  shows 0. Because FG% and FT% don't add up player by player, a high-volume, low-percentage
  player can come out below the weakest player (negative). With an open active slot, the
  baseline is the empty slot, so every player shows their full contribution.
- In tactical mode the opponent's roster is scored for the opponent.

Swapping a roster player for a free agent gains about the difference in their xLift.

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
of others. Under each-category scoring (see [the overview](overview.md)) punting costs more: every
category is a W or L in the standings, every week.

When looking strategically, the number of games matters less, since we are looking at a longer time window
where players' games played average out.  Another factor, however, becomes important, which is injury-proneness.
A player's tendency to become injured and not play impacts the bottom line.

The final comparison should be done against all teams. Under most-categories scoring, a team that can reliably
win against all teams in 5 categories is a great team. Under each-category scoring, 5–4 is a middling week:
what matters is the expected number of categories won against the whole league.

## The UI

The UI should consist of two primary sections: the simulation visualization and the player picker sidebar.

### Simulation Visualizer

The simulation visualization should show the result of the Monte Carlo simulation across all teams.

It should prominently show the team name, manager and projected W-L score.
In strategic mode, an overall W-L score is computed by matching the selected team against each other team and
counts the overall matchup wins and losses. In tactical mode, the W-L score is computed only looking at the current
matchup for the selected team.

How the record reads depends on the league's standings rule:

- **Each category** (our league): the headline, **Aggregated Record**, is the combined H2H score: the
  **expected category record**, equal to the H2H table's Total. For each category and
  opponent, the chances of a win, loss and tie across the simulations are added up and shown rounded to whole
  numbers, e.g. 58–45–5 in
  strategic mode (every other team once), with the standings win % (W + ½T) ÷ total; in tactical mode it is
  this week's projected record against the current opponent, the score so far plus the games left. The H2H
  table lists each opponent's expected category record, and roster moves show the change in
  expected wins between the rounded records. There is no matchup result, so no loss↔win flips.
- **Most categories**: the strategic headline counts matchup wins and losses (a matchup is a W if won in more
  than half the simulations), the tactical headline is the chance to win the matchup, and the H2H table shows
  each matchup's chance to win and result.

In an each-category league, xLift and the radar's Win % measure exactly what the standings count.

**Focusing on an opponent** (strategic): clicking a team in the H2H table compares the page with that team
instead of the league, to show why the matchup goes the way it does. The radar shows only the two teams, and
its Win % view becomes each side's chance of winning each category in this matchup. In the per-category
table, the League column becomes the opponent's averages and Win % your chance of beating them. Each
category's distribution chart shows the opponent in place of the League Average, beside the League Leader.
Ranks, area scores and the league-shape charts stay league-wide. Clicking the team again returns to the
league; changing mode, team or league does too, and roster moves keep the focus.

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

In strategic mode, each category also shows the league's shape, so you can see which ranks are
cheap to gain and which aren't:

- **League shape**: every team's projected value, ordered by place, joined by a line. Even
  spacing means every place costs the same; clusters and cliffs show where it doesn't. Your
  team's dot is marked, and after a move a hollow marker shows where you were.
- **Against null**: the gap to reach each place, as bars, against the gap a league of the same
  size and spread would show if teams were normally distributed (a dotted line). A bar above the
  line is an unusually big step; below it, an unusually tight cluster. Your **climb** (the gap
  to move up one place) and your **cushion** (the gap to the team below) are marked.

### Player Picker 

On the right sidebar, we should list out all players not on selected team: free agents first,
then rostered players, each ordered by xLift for the selected team, highest first.
A search bar should be present at the top enable name-based filtering.
A '+' button to the left of each player should add the player to the selected team iff the roster has an empty slot.

An "empty slot" means an empty active slot. Reserve slots (IL, NA) are not available for moves.
A player can occupy IL/NA only if they were there in the original roster. An added or swapped
player always takes an active slot, even if injured. Players already in a reserve slot stay there
unless dropped. They do not count against active capacity, and they do not contribute to the
simulation.

If the player is a free agent, we simply add the player and run the simulation.
If the player is on another team, we must select a player on the roster or a free agent in the list to swap with.
That team receives the selected player in return. A roster player makes it a 1-for-1 trade, which needs no empty
slot. A free agent goes to the other team, and the acquired player then needs an empty active slot on the selected
team.

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
