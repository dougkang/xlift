"""Rebuild the hypothetical league for a request: loaded snapshot + moves (research R7)."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.exc import NoResultFound

from ffmodel.core.data import get_league, get_player_details
from ffmodel.core.data.models import FantasyTeamView, LeagueSnapshot, PlayerSummary
from ffmodel.core.scenario import Add, Drop, Scenario, Swap, apply_all, from_snapshot


class NotFound(LookupError):
    pass


@dataclass(frozen=True)
class LeagueState:
    snapshot: LeagueSnapshot
    teams: dict[int, FantasyTeamView]
    names: dict[int, str]
    scenario: Scenario
    base_owner: dict[int, int]
    info: dict[int, tuple[PlayerSummary, str]]  # player -> (summary, latest status)


def _move_players(moves: Sequence) -> set[int]:
    ids: set[int] = set()
    for m in moves:
        if isinstance(m, Drop | Add):
            ids.add(m.player_id)
        elif isinstance(m, Swap):
            ids |= {m.acquire_id, m.give_id}
    return ids


def load_state(conn, league_id: int, team_id: int, moves: Sequence = ()) -> LeagueState:
    try:
        snapshot = get_league(conn, league_id)
    except NoResultFound as exc:
        raise NotFound(f"no league {league_id}") from exc
    teams = {t.fantasy_team_id: t for t in snapshot.teams}
    if team_id not in teams:
        raise NotFound(f"no team {team_id} in league {league_id}")
    names = {tid: t.name for tid, t in teams.items()}

    info = {r.player.player_id: (r.player, r.status) for t in snapshot.teams for r in t.roster}
    extra = _move_players(moves) - info.keys()
    if extra:
        info |= get_player_details(conn, player_ids=sorted(extra))
    base = from_snapshot(snapshot)
    scenario = apply_all(base, team_id, moves, known=info.keys(), names=names)
    return LeagueState(snapshot, teams, names, scenario, dict(base.owner), info)
