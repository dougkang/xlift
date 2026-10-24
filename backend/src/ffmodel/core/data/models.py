"""Read-model types returned by ffmodel.core.data (contracts/read-api.md)."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PlayerSummary:
    player_id: int
    full_name: str
    positions: tuple[str, ...]
    current_team: str | None
    is_active: bool


@dataclass(frozen=True)
class PlayerGameLine:
    game_id: int
    season_id: str
    game_date: date
    team: str
    opponent: str
    minutes: float
    fgm: int
    fga: int
    fg3m: int
    fg3a: int
    ftm: int
    fta: int
    oreb: int
    dreb: int
    reb: int
    ast: int
    stl: int
    blk: int
    tov: int
    pf: int
    pts: int
    plus_minus: int | None


@dataclass(frozen=True)
class GameWindow:
    player_id: int
    requested: int
    found: int
    games: tuple[PlayerGameLine, ...]

    @property
    def is_short(self) -> bool:
        return self.found < self.requested


@dataclass(frozen=True)
class Availability:
    player_id: int
    team_games: int
    games_played: int

    @property
    def games_missed(self) -> int:
        return self.team_games - self.games_played


@dataclass(frozen=True)
class LeagueSettings:
    league_id: int
    league_key: str
    name: str
    season_id: str
    scoring_format_id: str
    active_roster_capacity: int


@dataclass(frozen=True)
class RosterPlayer:
    player: PlayerSummary
    slot: str
    status: str


@dataclass(frozen=True)
class FantasyTeamView:
    fantasy_team_id: int
    source_team_key: str
    name: str
    manager: str
    roster: tuple[RosterPlayer, ...]


@dataclass(frozen=True)
class LeagueSnapshot:
    settings: LeagueSettings
    teams: tuple[FantasyTeamView, ...]


@dataclass(frozen=True)
class DataFreshness:
    nba_data_loaded_at: str | None
    roster_as_of: str | None
    matchup_as_of: str | None = None


# The contract's fixed stat vocabulary for matchup totals (migration 0002, research R5).
MATCHUP_STATS = ("fgm", "fga", "fg3m", "ftm", "fta", "reb", "ast", "stl", "blk", "tov", "pts")


@dataclass(frozen=True)
class MatchupLine:
    """One team's week-to-date totals in the current matchup (005)."""

    team_id: int
    opponent_id: int
    totals: dict[str, int]


@dataclass(frozen=True)
class MatchupState:
    """A league's current matchup: games on or before `as_of` are in the totals."""

    league_id: int
    week: int
    period_start: date
    period_end: date
    as_of: date
    loaded_at: str | None
    lines: dict[int, MatchupLine]
