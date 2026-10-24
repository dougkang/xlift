"""Builds player projections from the data contract (research R1, R4, R5)."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import text

from ffmodel.core.data import count_team_games_bulk, get_availability, get_last_n_games_bulk
from ffmodel.core.model.fit import PlayerProjection, availability_rate, fit_projection
from ffmodel.core.scoring import ScoringFormat


def build_projections(
    conn,
    player_ids: Sequence[int],
    fmt: ScoringFormat,
    *,
    window: int,
    as_of: date,
    period: tuple[date, date] | None = None,
) -> dict[int, PlayerProjection]:
    ids = sorted(set(player_ids))
    windows = get_last_n_games_bulk(conn, ids, window, as_of=as_of)
    # `period` is the remaining-games window, used as given: tactical picks games by date after
    # the matchup's as-of, whatever their status in our data (005 research R2).
    remaining = (
        count_team_games_bulk(conn, ids, period[0], period[1], statuses=("scheduled", "final"))
        if period
        else dict.fromkeys(ids, 0)
    )
    out = {}
    for pid in ids:
        w = windows[pid]
        proj = fit_projection(pid, w, fmt.base_stats)
        avail = None
        if w.found:
            start = min(g.game_date for g in w.games)
            if w.found < w.requested:
                # The window holds every game the player has; count misses back to the start of
                # their earliest stint, not just from their first appearance (research R4).
                first_stint = conn.execute(
                    text("SELECT MIN(start_date) FROM player_team_stint WHERE player_id = :p"),
                    {"p": pid},
                ).scalar_one()
                if first_stint:
                    start = min(start, date.fromisoformat(first_stint))
            span = get_availability(conn, pid, start, as_of)
            avail = availability_rate(w.found, span.team_games)
        out[pid] = PlayerProjection(
            proj.player_id,
            proj.games_found,
            proj.games_requested,
            proj.mean,
            proj.chol,
            proj.mean_stderr,
            availability=avail,
            games_remaining=remaining.get(pid, 0),
        )
    return out
