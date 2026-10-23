from sqlalchemy import text

from tests.invariants import assert_contract_invariants

TABLES = [
    "season",
    "nba_team",
    "nba_team_external_id",
    "player",
    "player_external_id",
    "game",
    "player_game",
    "player_team_stint",
    "fantasy_league",
    "manager",
    "fantasy_team",
    "roster_entry",
    "player_status",
]


def test_fixture_loads_and_satisfies_invariants(fixture_engine):
    with fixture_engine.connect() as conn:
        assert_contract_invariants(conn)
        for table in TABLES:
            assert conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() > 0, table
