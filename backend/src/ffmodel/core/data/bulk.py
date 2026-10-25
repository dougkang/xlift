"""Bulk reads for tools that need many players at once. Regular season only (FR-012)."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import date

from sqlalchemy import bindparam, text

from ffmodel.core.data.games import _STATS
from ffmodel.core.data.models import DataFreshness, GameWindow, PlayerGameLine

_LAST_N = f"""
SELECT * FROM (
  SELECT pg.player_id AS _pid, g.game_id, g.season_id, g.game_date,
         t.abbreviation AS team, o.abbreviation AS opponent,
         pg.minutes, {", ".join("pg." + s for s in _STATS)}, pg.plus_minus,
         ROW_NUMBER() OVER (PARTITION BY pg.player_id
                            ORDER BY g.game_date DESC, g.game_id DESC) AS _rn
  FROM player_game pg
  JOIN game g ON g.game_id = pg.game_id
  JOIN nba_team t ON t.team_id = pg.team_id
  JOIN nba_team o ON o.team_id = CASE WHEN g.home_team_id = pg.team_id
                                      THEN g.away_team_id ELSE g.home_team_id END
  WHERE pg.player_id IN :ids AND g.season_type = 'regular' AND g.game_date <= :as_of
) ranked
WHERE _rn <= :n
ORDER BY _pid, game_date DESC, game_id DESC
"""

_TEAM_GAMES = """
SELECT s.player_id, COUNT(DISTINCT g.game_id) FROM game g
JOIN player_team_stint s ON s.team_id IN (g.home_team_id, g.away_team_id)
WHERE s.player_id IN :ids
  AND g.season_type = 'regular'
  AND g.status IN :statuses
  AND g.game_date BETWEEN :a AND :b
  AND g.game_date BETWEEN s.start_date AND COALESCE(s.end_date, '9999-12-31')
GROUP BY s.player_id
"""


def get_last_n_games_bulk(
    conn, player_ids: Sequence[int], n: int, *, as_of: date
) -> dict[int, GameWindow]:
    ids = list(player_ids)
    games: dict[int, list] = defaultdict(list)
    if ids:
        stmt = text(_LAST_N).bindparams(bindparam("ids", expanding=True))
        # Positional rows: _pid, then PlayerGameLine's fields in order, then _rn. Building lines
        # directly (not via a dict per row) matters at 82-game windows for the whole pool.
        dates: dict[str, date] = {}
        for row in conn.execute(stmt, {"ids": ids, "as_of": as_of.isoformat(), "n": n}):
            day = dates.get(row[3]) or dates.setdefault(row[3], date.fromisoformat(row[3]))
            games[row[0]].append(PlayerGameLine(row[1], row[2], day, *row[4:-1]))
    return {
        pid: GameWindow(player_id=pid, requested=n, found=len(games[pid]), games=tuple(games[pid]))
        for pid in ids
    }


def count_team_games_bulk(
    conn,
    player_ids: Sequence[int],
    start: date,
    end: date,
    *,
    statuses: Sequence[str] = ("final", "scheduled"),
) -> dict[int, int]:
    ids = list(player_ids)
    counts = dict.fromkeys(ids, 0)
    if ids:
        stmt = text(_TEAM_GAMES).bindparams(
            bindparam("ids", expanding=True), bindparam("statuses", expanding=True)
        )
        params = {
            "ids": ids,
            "statuses": list(statuses),
            "a": start.isoformat(),
            "b": end.isoformat(),
        }
        counts.update(dict(conn.execute(stmt, params).all()))
    return counts


def get_players_with_games(conn, start: date, end: date) -> list[int]:
    """Every player with a regular-season game played in [start, end]."""
    rows = conn.execute(
        text(
            "SELECT DISTINCT pg.player_id FROM player_game pg JOIN game g ON g.game_id = pg.game_id"
            " WHERE g.season_type = 'regular' AND g.game_date BETWEEN :a AND :b"
            " ORDER BY pg.player_id"
        ),
        {"a": start.isoformat(), "b": end.isoformat()},
    )
    return [r[0] for r in rows]


def get_data_freshness(conn, league_id: int) -> DataFreshness:
    loaded = conn.execute(
        text(
            "SELECT MAX(finished_at) FROM load_run"
            " WHERE source = 'nba_stats' AND outcome = 'succeeded'"
        )
    ).scalar_one()
    roster = conn.execute(
        text(
            "SELECT MAX(s.as_of) FROM player_status s"
            " JOIN roster_entry re ON re.player_id = s.player_id WHERE re.league_id = :l"
        ),
        {"l": league_id},
    ).scalar_one()
    matchup = conn.execute(
        text("SELECT as_of FROM matchup_state WHERE league_id = :l"), {"l": league_id}
    ).scalar_one_or_none()
    return DataFreshness(nba_data_loaded_at=loaded, roster_as_of=roster, matchup_as_of=matchup)
