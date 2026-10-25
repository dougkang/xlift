"""The only read path from the data contract into the engine and tools (Constitution VI)."""

from ffmodel.core.data.availability import count_team_games, get_availability
from ffmodel.core.data.bulk import (
    count_team_games_bulk,
    get_data_freshness,
    get_last_n_games_bulk,
    get_players_with_games,
)
from ffmodel.core.data.games import get_last_n_games, get_player_history
from ffmodel.core.data.league import get_free_agents, get_league, list_leagues
from ffmodel.core.data.matchup import get_matchup_state
from ffmodel.core.data.models import (
    Availability,
    DataFreshness,
    FantasyTeamView,
    GameWindow,
    LeagueSettings,
    LeagueSnapshot,
    MatchupLine,
    MatchupState,
    PlayerGameLine,
    PlayerSummary,
    RosterPlayer,
)
from ffmodel.core.data.players import get_player, get_player_details, search_players

__all__ = [
    "Availability",
    "DataFreshness",
    "FantasyTeamView",
    "GameWindow",
    "LeagueSettings",
    "LeagueSnapshot",
    "MatchupLine",
    "MatchupState",
    "PlayerGameLine",
    "PlayerSummary",
    "RosterPlayer",
    "count_team_games",
    "count_team_games_bulk",
    "get_availability",
    "get_data_freshness",
    "get_free_agents",
    "get_league",
    "get_last_n_games",
    "get_last_n_games_bulk",
    "get_players_with_games",
    "get_matchup_state",
    "get_player",
    "get_player_details",
    "get_player_history",
    "list_leagues",
    "search_players",
]
