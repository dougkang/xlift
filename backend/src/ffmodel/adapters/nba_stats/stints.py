"""Derives player-team stints from appearances (research R3)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

DAY = timedelta(days=1)


@dataclass(frozen=True)
class Stint:
    team_id: int
    start_date: date
    end_date: date | None


def derive_stints(
    appearances: Iterable[tuple[date, int]],
    season_start: date,
    current_team_id: int | None = None,
    season_end: date | None = None,
) -> list[Stint]:
    """Stints for one player in one season.

    `current_team_id` applies only to the newest season; older seasons pass `season_end`,
    which closes the final stint at the end of the season.
    """
    runs: list[list] = []  # [team_id, first_date, last_date]
    for day, team in sorted(appearances):
        if runs and runs[-1][0] == team:
            runs[-1][2] = day
        else:
            runs.append([team, day, day])

    if not runs:
        if season_end is None and current_team_id is not None:
            return [Stint(current_team_id, season_start, None)]
        return []

    stints = []
    for i, (team, first, last) in enumerate(runs):
        start = season_start if i == 0 else first
        if i + 1 < len(runs):
            stints.append(Stint(team, start, runs[i + 1][1] - DAY))
        elif season_end is not None:
            stints.append(Stint(team, start, season_end))
        elif current_team_id == team:
            stints.append(Stint(team, start, None))
        elif current_team_id is None:
            stints.append(Stint(team, start, last))
        else:
            stints.append(Stint(team, start, last))
            stints.append(Stint(current_team_id, last + DAY, None))
    return stints
