"""The Fragility Penalty: how availability is estimated for the whole analysis (007 FR-013–FR-019).

Replaces each projection's availability before simulating and scoring (research R4). The
simulation reads availability only from the projection, so one substitution covers every
strategic result and xLift. Tactical odds use games remaining, so only xLift changes there.
"""

from dataclasses import replace
from datetime import date

from ffmodel.core.data import get_availability_history
from ffmodel.core.model import availability as av
from ffmodel.core.scenario.scenario import RESERVE
from ffmodel.tools.impact_analysis import cache


def apply(option: str, projections: dict, scenario, statuses: dict, conn, as_of: date) -> dict:
    """Projections with availability per `option`. Players without games stay unprojected.

    - none: 1.0, except 0.0 in any team's reserve (IL/IL+/NA) slot;
    - last15: as built (the most recent 15 games);
    - dab: dAB;
    - dab_tag: dAB × the injury tag's multiplier."""
    if option == "last15":
        return projections
    projected = [pid for pid, p in projections.items() if p.games_found > 0]
    if option == "none":
        reserve = {
            s.player_id for spots in scenario.rosters.values() for s in spots if s.slot == RESERVE
        }
        rate = {pid: 0.0 if pid in reserve else 1.0 for pid in projected}
    elif option in ("dab", "dab_tag"):
        rate = cache.dab(conn, projected, as_of)
        if option == "dab_tag":
            rate = {pid: r * av.tag_multiplier(statuses.get(pid)) for pid, r in rate.items()}
    else:
        raise ValueError(f"unknown fragility option {option!r}")
    return {
        pid: replace(p, availability=rate[pid]) if pid in rate else p
        for pid, p in projections.items()
    }


def dab_values(conn, player_ids, as_of: date) -> dict[int, float]:
    """dAB for each player at `as_of` (research R3)."""
    hist = get_availability_history(conn, player_ids, as_of)
    starts, cut = hist.season_starts, av.cut_after(as_of)
    return {
        pid: av.dab(
            av.age_counts(
                hist.played.get(pid),
                hist.team_games.get(pid),
                hist.missed.get(pid, []),
                starts,
                cut,
            )
            if len(starts)
            else None
        )
        for pid in player_ids
    }
