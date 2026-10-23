"""League reads (FR-022): settings, teams, rosters, statuses, free agents."""

from collections import defaultdict

from sqlalchemy import text

from ffmodel.core.data._rows import PLAYER_COLUMNS, PLAYER_FROM, player_summary
from ffmodel.core.data.models import (
    FantasyTeamView,
    LeagueSettings,
    LeagueSnapshot,
    PlayerSummary,
    RosterPlayer,
)

_SETTINGS = (
    "SELECT league_id, league_key, name, season_id, scoring_format_id, active_roster_capacity"
    " FROM fantasy_league"
)
_LATEST_STATUS = (
    "(SELECT s.status FROM player_status s WHERE s.player_id = p.player_id"
    " ORDER BY s.as_of DESC, s.source LIMIT 1)"
)


def list_leagues(conn) -> list[LeagueSettings]:
    rows = conn.execute(text(f"{_SETTINGS} ORDER BY league_key")).mappings()
    return [LeagueSettings(**r) for r in rows]


def get_league(conn, league_id: int) -> LeagueSnapshot:
    settings = (
        conn.execute(text(f"{_SETTINGS} WHERE league_id = :l"), {"l": league_id}).mappings().one()
    )
    teams = (
        conn.execute(
            text(
                "SELECT ft.fantasy_team_id, ft.source_team_key, ft.name, m.display_name AS manager"
                " FROM fantasy_team ft JOIN manager m ON m.manager_id = ft.manager_id"
                " WHERE ft.league_id = :l ORDER BY ft.source_team_key"
            ),
            {"l": league_id},
        )
        .mappings()
        .all()
    )
    roster = defaultdict(list)
    for r in conn.execute(
        text(
            f"SELECT re.fantasy_team_id, re.slot, {_LATEST_STATUS} AS status, {PLAYER_COLUMNS}"
            " FROM roster_entry re JOIN player p ON p.player_id = re.player_id"
            " LEFT JOIN nba_team t ON t.team_id = p.current_team_id"
            " WHERE re.league_id = :l"
            " ORDER BY CASE re.slot WHEN 'active' THEN 0 ELSE 1 END, p.full_name"
        ),
        {"l": league_id},
    ).mappings():
        roster[r["fantasy_team_id"]].append(
            RosterPlayer(player=player_summary(r), slot=r["slot"], status=r["status"] or "healthy")
        )
    return LeagueSnapshot(
        settings=LeagueSettings(**settings),
        teams=tuple(
            FantasyTeamView(
                fantasy_team_id=t["fantasy_team_id"],
                source_team_key=t["source_team_key"],
                name=t["name"],
                manager=t["manager"],
                roster=tuple(roster[t["fantasy_team_id"]]),
            )
            for t in teams
        ),
    )


def get_free_agents(conn, league_id: int) -> list[PlayerSummary]:
    rows = conn.execute(
        text(
            f"SELECT {PLAYER_COLUMNS} FROM {PLAYER_FROM}"
            " WHERE p.is_active = 1 AND p.player_id NOT IN"
            " (SELECT player_id FROM roster_entry WHERE league_id = :l)"
            " ORDER BY p.full_name, p.player_id"
        ),
        {"l": league_id},
    ).mappings()
    return [player_summary(r) for r in rows]
