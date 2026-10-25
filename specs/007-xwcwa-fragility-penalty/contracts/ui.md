# UI Contract Changes: xLift and the Fragility Penalty

Base: [002 ui.md](../../002-impact-analysis/contracts/ui.md). Style per `docs/style.md`; nothing
new visually. Help text never mentions file names (project rule).

## Controls

- **Fragility Penalty**, a dropdown next to *Last X games*.
  - Options: **None**, **Last 15**, **dAB**, **dAB × tag**. The default is **dAB × tag**.
  - Changing it re-runs the analysis, like the other settings.

## Roster tables (yours, and the opponent's in tactical mode)

- A new numeric column **xLift**, after *Pos* (and *G* in tactical), signed with two decimals
  (e.g. `+1.27`, `0.00`, `−0.40`). "–" when null.
- Reserve rows keep their muted style, which marks them as not counted in the team's totals;
  their xLift is shown as in the API.

## Player picker

- A new numeric column **xLift** in the same format.
- Rows appear in the server's order (xLift, highest first, within free agents, then rostered
  players). The client doesn't re-sort.

## Help

- **Analysis settings → Fragility Penalty**: "how often each player is expected to play. None:
  everyone outside an IL slot plays every game. Last 15: games played over the last 15. dAB:
  a multi-season estimate that forgives old absences. dAB × tag: dAB adjusted for current injury
  tags."
- **Roster / Players → xLift**: "expected weekly category wins this player adds to the team
  shown, across every opponent, compared with the team's weakest active player (who shows 0),
  or an empty slot, if one is open or an active player has no games. Swapping a roster player
  for a free agent gains about the difference."
