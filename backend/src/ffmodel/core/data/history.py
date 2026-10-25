"""Multi-season availability history for dAB (007 research R3). Regular season, final games only.

Reads only the requested players' games, as the availability report's loader does for everyone.
Dates are ISO strings.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

import numpy as np
from sqlalchemy import bindparam, text

_PLAYED = """
SELECT pg.player_id, g.game_date FROM player_game pg
JOIN game g ON g.game_id = pg.game_id
WHERE pg.player_id IN :ids AND g.season_type = 'regular' AND g.status = 'final'
  AND g.game_date <= :as_of
ORDER BY pg.player_id, g.game_date
"""

# Team games are joined to stints here rather than in SQL: the join over every season costs
# far more than reading the few thousand games and stints (007 T032).
_GAMES = """
SELECT game_id, game_date, home_team_id, away_team_id FROM game
WHERE season_type = 'regular' AND status = 'final' AND game_date <= :as_of
"""

_STINTS = """
SELECT player_id, team_id, start_date, COALESCE(end_date, '9999-12-31') FROM player_team_stint
WHERE player_id IN :ids
"""

_SEASONS = """
SELECT season_id, MIN(game_date), MAX(game_date), COUNT(*) FROM game
WHERE season_type = 'regular' AND status = 'final' AND game_date <= :as_of
GROUP BY season_id ORDER BY season_id
"""

_DAYS = """
SELECT DISTINCT season_id, game_date FROM game
WHERE season_type = 'regular' AND status = 'final' AND game_date <= :as_of
ORDER BY game_date
"""

TEAMS = 30  # a missed season is a team's worth of games: 2 × season games ÷ teams


@dataclass(frozen=True)
class AvailabilityHistory:
    seasons: list[tuple[str, str, str, int]]  # (season_id, first day, last day, games)
    played: dict[int, np.ndarray]  # player -> ascending dates played
    team_games: dict[int, np.ndarray]  # player -> ascending team-game dates on the roster
    # player -> inferred missed seasons: (evenly spaced game days, known from = the return)
    missed: dict[int, list[tuple[np.ndarray, str]]] = field(default_factory=dict)

    @property
    def season_starts(self) -> np.ndarray:
        return np.array([s[1] for s in self.seasons])


def _team_games(conn, ids: list[int], params: dict) -> dict[int, list[str]]:
    """Each player's distinct team-game dates while on a team's roster (by stint)."""
    by_team: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for gid, d, home, away in conn.execute(text(_GAMES), params):
        by_team[home].append((d, gid))
        by_team[away].append((d, gid))
    sched = {}
    for t, games in by_team.items():
        games.sort()
        sched[t] = (np.array([d for d, _ in games]), np.array([g for _, g in games]))
    seen: dict[int, dict[int, str]] = defaultdict(dict)  # player -> game id -> date
    stints = text(_STINTS).bindparams(bindparam("ids", expanding=True))
    for pid, team_id, start, end in conn.execute(stints, {"ids": ids}):
        if team_id not in sched:
            continue
        dates, gids = sched[team_id]
        lo, hi = np.searchsorted(dates, start, "left"), np.searchsorted(dates, end, "right")
        seen[pid].update(zip(gids[lo:hi].tolist(), dates[lo:hi].tolist(), strict=True))
    return {pid: list(games.values()) for pid, games in seen.items()}


def get_availability_history(conn, player_ids: Sequence[int], as_of: date) -> AvailabilityHistory:
    ids = sorted(set(player_ids))
    params = {"as_of": as_of.isoformat()}
    seasons = [tuple(r) for r in conn.execute(text(_SEASONS), params)]
    played: dict[int, list[str]] = defaultdict(list)
    team: dict[int, list[str]] = {}
    if ids:
        for pid, d in conn.execute(
            text(_PLAYED).bindparams(bindparam("ids", expanding=True)), params | {"ids": ids}
        ):
            played[pid].append(d)
        team = _team_games(conn, ids, params)
    hist = AvailabilityHistory(
        seasons=seasons,
        played={p: np.array(d) for p, d in played.items()},
        team_games={p: np.sort(np.array(d)) for p, d in team.items()},
    )
    if not seasons:
        return hist
    # Missed seasons: a season with no games between two with games (research R3).
    season_days: dict[str, list[str]] = defaultdict(list)
    for sid, d in conn.execute(text(_DAYS), params):
        season_days[sid].append(d)
    starts = hist.season_starts
    for pid, p in hist.played.items():
        of = np.searchsorted(starts, p, side="right") - 1
        played_in = set(of.tolist())
        for k in range(min(played_in) + 1, max(played_in)):
            if k in played_in:
                continue
            sid, _, _, n = seasons[k]
            all_days = np.array(season_days[sid])
            per_team = round(2 * n / TEAMS)
            pick = all_days[np.linspace(0, len(all_days) - 1, per_team).round().astype(int)]
            back = str(p[of > k][0])
            hist.missed.setdefault(pid, []).append((pick, back))
    return hist
