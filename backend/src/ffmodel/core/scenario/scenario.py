"""Immutable league scenario: the loaded rosters plus hypothetical moves (Constitution VII).

Nothing here touches the database; Reset is simply an empty move list.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # type-only: importing ffmodel.core.data would load the database layer
    from ffmodel.core.data.models import LeagueSettings, LeagueSnapshot

ACTIVE, RESERVE = "active", "reserve"


@dataclass(frozen=True)
class RosterSpot:
    player_id: int
    slot: str


class ScenarioInvariantError(AssertionError):
    pass


@dataclass(frozen=True)
class Scenario:
    league: LeagueSettings
    rosters: Mapping[int, tuple[RosterSpot, ...]]
    base_reserve: frozenset[int]

    @cached_property
    def owner(self) -> Mapping[int, int]:
        return MappingProxyType(
            {spot.player_id: team for team, spots in self.rosters.items() for spot in spots}
        )

    def active_count(self, team_id: int) -> int:
        return sum(1 for s in self.rosters[team_id] if s.slot == ACTIVE)

    def open_active_slots(self, team_id: int) -> int:
        return max(0, self.league.active_roster_capacity - self.active_count(team_id))

    def active_players(self, team_id: int) -> list[int]:
        return [s.player_id for s in self.rosters[team_id] if s.slot == ACTIVE]

    def check_invariants(self) -> None:
        seen: set[int] = set()
        for team, spots in self.rosters.items():
            if self.active_count(team) > self.league.active_roster_capacity:
                raise ScenarioInvariantError(f"team {team} exceeds active capacity")
            for spot in spots:
                if spot.player_id in seen:
                    raise ScenarioInvariantError(f"player {spot.player_id} on two teams")
                seen.add(spot.player_id)
                if spot.slot == RESERVE and spot.player_id not in self.base_reserve:
                    raise ScenarioInvariantError(f"player {spot.player_id} moved into reserve")


def from_snapshot(snapshot: LeagueSnapshot) -> Scenario:
    rosters = {
        team.fantasy_team_id: tuple(RosterSpot(r.player.player_id, r.slot) for r in team.roster)
        for team in snapshot.teams
    }
    reserve = frozenset(
        r.player.player_id for team in snapshot.teams for r in team.roster if r.slot == RESERVE
    )
    return Scenario(
        league=snapshot.settings, rosters=MappingProxyType(rosters), base_reserve=reserve
    )


# --- Moves (data-model.md transitions, research R7) -----------------------------------------


# Each move records the team it was made for (`team_id`), so moves stay attached to that team
# when the user switches the selected team. `None` means "the selected team".


@dataclass(frozen=True)
class Drop:
    player_id: int
    team_id: int | None = None


@dataclass(frozen=True)
class Add:
    player_id: int
    team_id: int | None = None


@dataclass(frozen=True)
class Swap:
    acquire_id: int
    give_id: int
    team_id: int | None = None


Move = Drop | Add | Swap


class MoveError(ValueError):
    def __init__(self, code: str, message: str, move_index: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.move_index = move_index


def _with(scenario: Scenario, rosters: dict[int, tuple[RosterSpot, ...]]) -> Scenario:
    return Scenario(
        league=scenario.league,
        rosters=MappingProxyType(rosters),
        base_reserve=scenario.base_reserve,
    )


def _check_capacity(scenario: Scenario, team_ids, names: Mapping[int, str]) -> None:
    for tid in team_ids:
        if scenario.active_count(tid) > scenario.league.active_roster_capacity:
            raise MoveError(
                "NO_ACTIVE_SLOT", f"{names.get(tid, f'Team {tid}')} has no open active slot"
            )


def apply(
    scenario: Scenario,
    team_id: int,
    move: Move,
    *,
    known=None,
    names: Mapping[int, str] | None = None,
) -> Scenario:
    """Apply one move; returns a new Scenario or raises MoveError.

    The move acts for `move.team_id` when set, otherwise for the selected `team_id`.
    """
    names = names or {}
    if move.team_id is not None:
        if move.team_id not in scenario.rosters:
            raise MoveError("UNKNOWN_TEAM", f"Unknown team {move.team_id}")
        team_id = move.team_id
    owner = scenario.owner
    rosters = dict(scenario.rosters)
    me = names.get(team_id, "Your team")

    def require_known(pid: int) -> None:
        if known is not None and pid not in known:
            raise MoveError("UNKNOWN_PLAYER", f"Unknown player {pid}")

    def without(tid: int, pid: int) -> tuple[RosterSpot, ...]:
        return tuple(s for s in rosters[tid] if s.player_id != pid)

    if isinstance(move, Drop):
        require_known(move.player_id)
        if owner.get(move.player_id) != team_id:
            raise MoveError("NOT_ON_TEAM", f"Player {move.player_id} is not on {me}")
        rosters[team_id] = without(team_id, move.player_id)
        return _with(scenario, rosters)

    if isinstance(move, Add):
        require_known(move.player_id)
        if move.player_id in owner:
            raise MoveError("NOT_FREE_AGENT", f"Player {move.player_id} is not a free agent")
        if scenario.open_active_slots(team_id) == 0:
            raise MoveError("NO_ACTIVE_SLOT", f"{me} has no open active slot")
        rosters[team_id] = rosters[team_id] + (RosterSpot(move.player_id, ACTIVE),)
        return _with(scenario, rosters)

    if isinstance(move, Swap):
        require_known(move.acquire_id)
        require_known(move.give_id)
        other = owner.get(move.acquire_id)
        if other == team_id:
            raise MoveError("SAME_TEAM", f"Player {move.acquire_id} is already on {me}")
        if other is None:
            raise MoveError("NOT_ON_TEAM", f"Player {move.acquire_id} is a free agent; add them")
        giver = owner.get(move.give_id)
        if giver not in (team_id, None):
            raise MoveError("NOT_ON_TEAM", f"Player {move.give_id} must be on {me} or a free agent")
        if giver == team_id:
            rosters[team_id] = without(team_id, move.give_id)
        rosters[other] = without(other, move.acquire_id) + (RosterSpot(move.give_id, ACTIVE),)
        rosters[team_id] = rosters[team_id] + (RosterSpot(move.acquire_id, ACTIVE),)
        result = _with(scenario, rosters)
        _check_capacity(result, (team_id, other), names)
        return result

    raise MoveError("UNKNOWN_MOVE", f"Unknown move {move!r}")


def apply_all(
    scenario: Scenario,
    team_id: int,
    moves,
    *,
    known=None,
    names: Mapping[int, str] | None = None,
) -> Scenario:
    for index, move in enumerate(moves):
        try:
            scenario = apply(scenario, team_id, move, known=known, names=names)
        except MoveError as exc:
            exc.move_index = index
            raise
    scenario.check_invariants()
    return scenario
