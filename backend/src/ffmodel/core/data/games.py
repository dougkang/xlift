"""Game history reads (FR-020, FR-020a). Regular season only (FR-012)."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import bindparam, text

from ffmodel.core.data.models import GameWindow, PlayerGameLine

_STATS = (
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "oreb",
    "dreb",
    "reb",
    "ast",
    "stl",
    "blk",
    "tov",
    "pf",
    "pts",
)
_SELECT = f"""
SELECT g.game_id, g.season_id, g.game_date, t.abbreviation AS team, o.abbreviation AS opponent,
       pg.minutes, {", ".join("pg." + s for s in _STATS)}, pg.plus_minus
FROM player_game pg
JOIN game g ON g.game_id = pg.game_id
JOIN nba_team t ON t.team_id = pg.team_id
JOIN nba_team o ON o.team_id = CASE WHEN g.home_team_id = pg.team_id
                                    THEN g.away_team_id ELSE g.home_team_id END
WHERE pg.player_id = :p AND g.season_type = 'regular'
"""
_ORDER = " ORDER BY g.game_date DESC, g.game_id DESC"


def _line(row) -> PlayerGameLine:
    data = dict(row)
    data["game_date"] = date.fromisoformat(data["game_date"])
    return PlayerGameLine(**data)


def get_last_n_games(conn, player_id: int, n: int, *, as_of: date | None = None) -> GameWindow:
    as_of = as_of or date.today()
    rows = conn.execute(
        text(_SELECT + " AND g.game_date <= :as_of" + _ORDER + " LIMIT :n"),
        {"p": player_id, "as_of": as_of.isoformat(), "n": n},
    ).mappings()
    games = tuple(_line(r) for r in rows)
    return GameWindow(player_id=player_id, requested=n, found=len(games), games=games)


def get_player_history(
    conn, player_id: int, *, seasons: Sequence[str] | None = None
) -> list[PlayerGameLine]:
    if seasons:
        stmt = text(_SELECT + " AND g.season_id IN :seasons" + _ORDER).bindparams(
            bindparam("seasons", expanding=True)
        )
        params = {"p": player_id, "seasons": list(seasons)}
    else:
        stmt, params = text(_SELECT + _ORDER), {"p": player_id}
    return [_line(r) for r in conn.execute(stmt, params).mappings()]
