"""Shared SQL fragments and row mappers for core reads."""

from ffmodel.core.data.models import PlayerSummary

PLAYER_COLUMNS = (
    "p.player_id, p.full_name, p.positions, p.is_active, t.abbreviation AS current_team"
)
PLAYER_FROM = "player p LEFT JOIN nba_team t ON t.team_id = p.current_team_id"


def player_summary(row) -> PlayerSummary:
    return PlayerSummary(
        player_id=row["player_id"],
        full_name=row["full_name"],
        positions=tuple(row["positions"].split(",")) if row["positions"] else (),
        current_team=row["current_team"],
        is_active=bool(row["is_active"]),
    )
