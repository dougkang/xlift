"""Contract invariants that DDL alone cannot express (data-model.md)."""

from sqlalchemy import text


def assert_contract_invariants(conn) -> None:
    overlaps = conn.execute(
        text(
            "SELECT a.player_id, a.start_date, b.start_date FROM player_team_stint a"
            " JOIN player_team_stint b ON a.player_id = b.player_id AND a.start_date < b.start_date"
            " WHERE COALESCE(a.end_date, '9999-12-31') >= b.start_date"
        )
    ).all()
    assert not overlaps, f"overlapping stints: {overlaps}"

    wrong_team = conn.execute(
        text(
            "SELECT pg.game_id, pg.player_id FROM player_game pg JOIN game g USING (game_id)"
            " WHERE pg.team_id NOT IN (g.home_team_id, g.away_team_id)"
        )
    ).all()
    assert not wrong_team, f"player_game team not in game: {wrong_team}"

    not_final = conn.execute(
        text(
            "SELECT pg.game_id FROM player_game pg JOIN game g USING (game_id)"
            " WHERE g.status <> 'final'"
        )
    ).all()
    assert not not_final, f"box scores for non-final games: {not_final}"

    over_cap = conn.execute(
        text(
            "SELECT ft.fantasy_team_id, COUNT(*) FROM roster_entry re"
            " JOIN fantasy_team ft USING (fantasy_team_id)"
            " JOIN fantasy_league fl ON fl.league_id = ft.league_id"
            " WHERE re.slot = 'active'"
            " GROUP BY ft.fantasy_team_id, fl.active_roster_capacity"
            " HAVING COUNT(*) > fl.active_roster_capacity"
        )
    ).all()
    assert not over_cap, f"teams over active capacity: {over_cap}"

    cross_league = conn.execute(
        text(
            "SELECT re.player_id FROM roster_entry re JOIN fantasy_team ft USING (fantasy_team_id)"
            " WHERE ft.league_id <> re.league_id"
        )
    ).all()
    assert not cross_league, f"roster entries on another league's team: {cross_league}"
