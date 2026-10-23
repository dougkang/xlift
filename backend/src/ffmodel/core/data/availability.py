"""Games in a date range and missed games, by team stint (FR-021). Regular season only."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import bindparam, text

from ffmodel.core.data.models import Availability

_TEAM_GAMES = """
SELECT COUNT(DISTINCT g.game_id) FROM game g
JOIN player_team_stint s ON s.team_id IN (g.home_team_id, g.away_team_id)
WHERE s.player_id = :p
  AND g.season_type = 'regular'
  AND g.status IN :statuses
  AND g.game_date BETWEEN :a AND :b
  AND g.game_date BETWEEN s.start_date AND COALESCE(s.end_date, '9999-12-31')
"""

_PLAYED = """
SELECT COUNT(*) FROM player_game pg JOIN game g ON g.game_id = pg.game_id
WHERE pg.player_id = :p AND g.season_type = 'regular' AND g.status = 'final'
  AND g.game_date BETWEEN :a AND :b
"""


def count_team_games(
    conn,
    player_id: int,
    start: date,
    end: date,
    *,
    statuses: Sequence[str] = ("final", "scheduled"),
) -> int:
    stmt = text(_TEAM_GAMES).bindparams(bindparam("statuses", expanding=True))
    return conn.execute(
        stmt,
        {"p": player_id, "statuses": list(statuses), "a": start.isoformat(), "b": end.isoformat()},
    ).scalar_one()


def get_availability(conn, player_id: int, start: date, end: date) -> Availability:
    team_games = count_team_games(conn, player_id, start, end, statuses=("final",))
    played = conn.execute(
        text(_PLAYED), {"p": player_id, "a": start.isoformat(), "b": end.isoformat()}
    ).scalar_one()
    return Availability(player_id=player_id, team_games=team_games, games_played=played)
