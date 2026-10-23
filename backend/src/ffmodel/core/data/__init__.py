"""The only read path from the data contract into the engine and tools (Constitution VI)."""

from ffmodel.core.data.availability import count_team_games, get_availability
from ffmodel.core.data.games import get_last_n_games, get_player_history
from ffmodel.core.data.league import get_free_agents, get_league, list_leagues
from ffmodel.core.data.models import (
    Availability,
    FantasyTeamView,
    GameWindow,
    LeagueSettings,
    LeagueSnapshot,
    PlayerGameLine,
    PlayerSummary,
    RosterPlayer,
)
from ffmodel.core.data.players import get_player, search_players

__all__ = [
    "Availability",
    "FantasyTeamView",
    "GameWindow",
    "LeagueSettings",
    "LeagueSnapshot",
    "PlayerGameLine",
    "PlayerSummary",
    "RosterPlayer",
    "count_team_games",
    "get_availability",
    "get_free_agents",
    "get_league",
    "get_last_n_games",
    "get_player",
    "get_player_history",
    "list_leagues",
    "search_players",
]
