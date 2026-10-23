"""Immutable league scenario: the loaded rosters plus hypothetical moves (Constitution VII).

Nothing here touches the database; Reset is simply an empty move list.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType

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
