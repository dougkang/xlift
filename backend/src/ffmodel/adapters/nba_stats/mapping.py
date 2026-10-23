"""Pure mappings from nba_api records to contract rows (research R1, R2)."""

from ffmodel.contract.seasons import current_season, previous_season, season_label

__all__ = ["current_season", "previous_season", "season_label"]

SEASON_TYPE_BY_PREFIX = {
    "001": "preseason",
    "002": "regular",
    "003": "all_star",
    "004": "playoffs",
    "005": "play_in",
    "006": "cup_final",
}
_POSITION_ORDER = ("G", "F", "C")
_BOX_COLUMNS = {
    "FGM": "fgm",
    "FGA": "fga",
    "FG3M": "fg3m",
    "FG3A": "fg3a",
    "FTM": "ftm",
    "FTA": "fta",
    "OREB": "oreb",
    "DREB": "dreb",
    "REB": "reb",
    "AST": "ast",
    "STL": "stl",
    "BLK": "blk",
    "TOV": "tov",
    "PF": "pf",
    "PTS": "pts",
}


def season_type_from_game_id(game_id: str) -> str:
    try:
        return SEASON_TYPE_BY_PREFIX[str(game_id)[:3]]
    except KeyError:
        raise ValueError(f"unknown game id prefix: {game_id!r}") from None


def game_status(status: int, postponed: str | None) -> str:
    if postponed == "Y":
        return "postponed"
    return "final" if int(status) == 3 else "scheduled"


def normalize_positions(position: str | None) -> str | None:
    parts = {p for p in (position or "").split("-") if p}
    ordered = [p for p in _POSITION_ORDER if p in parts]
    return ",".join(ordered) or None


def season_from_season_id(season_id: str) -> str:
    return season_label(int(str(season_id)[1:]))


def box_score_row(record: dict, game_id: int, player_id: int, team_id: int) -> dict:
    row = {
        "game_id": game_id,
        "player_id": player_id,
        "team_id": team_id,
        "minutes": float(record["MIN"] or 0),
    }
    for src, dst in _BOX_COLUMNS.items():
        row[dst] = int(record[src] or 0)
    pm = record.get("PLUS_MINUS")
    row["plus_minus"] = None if pm is None else int(pm)
    return row


def schedule_game_row(record: dict, season: str, home_id: int, away_id: int) -> dict:
    return {
        "season_id": season,
        "season_type": season_type_from_game_id(record["gameId"]),
        "game_date": record["gameDateEst"][:10],
        "home_team_id": home_id,
        "away_team_id": away_id,
        "status": game_status(record["gameStatus"], record.get("postponedStatus")),
    }
