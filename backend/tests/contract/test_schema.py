from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ffmodel.contract.migrate import current_version, migrate

REPO = Path(__file__).resolve().parents[3]
CONTRACT_DDL = REPO / "specs/001-league-data-schema/contracts/schema.sql"
MIGRATION = REPO / "backend/src/ffmodel/contract/migrations/0001_initial.sql"

BASE_ROWS = [
    "INSERT INTO season VALUES ('2026-27', '2026-10-20', '2027-04-11')",
    "INSERT INTO nba_team VALUES (1, 'LAL', 'Los Angeles', 'Lakers')",
    "INSERT INTO nba_team VALUES (2, 'GSW', 'Golden State', 'Warriors')",
    "INSERT INTO player VALUES (1, 'A B', 'A', 'B', 'a b', 'G', 1, 1)",
    "INSERT INTO game VALUES (1, '2026-27', 'regular', '2026-10-20', 1, 2, 'final')",
    "INSERT INTO fantasy_league VALUES (1, 'lg', 'League', '2026-27', '9cat_h2h', 10)",
    "INSERT INTO manager VALUES (1, 1, 'Ann')",
    "INSERT INTO fantasy_team VALUES (1, 1, 't.01', 'Alpha', 1)",
]

GOOD_BOX = dict(
    minutes=30,
    fgm=5,
    fga=10,
    fg3m=1,
    fg3a=3,
    ftm=2,
    fta=4,
    oreb=1,
    dreb=4,
    reb=5,
    ast=3,
    stl=1,
    blk=0,
    tov=2,
    pf=1,
    pts=13,
)


def box(**overrides):
    vals = {**GOOD_BOX, **overrides}
    cols = ", ".join(vals)
    nums = ", ".join(str(v) for v in vals.values())
    return f"INSERT INTO player_game (game_id, player_id, team_id, {cols}) VALUES (1, 1, 1, {nums})"


GAME2 = "INSERT INTO game VALUES (2, '2026-27', "

VIOLATIONS = {
    "season_id_length": "INSERT INTO season VALUES ('2026', '2026-10-01', '2027-04-01')",
    "season_end_before_start": "INSERT INTO season VALUES ('2027-28', '2027-10-01', '2027-09-01')",
    "team_abbreviation_unique": "INSERT INTO nba_team VALUES (3, 'LAL', 'X', 'Y')",
    "player_is_active_bool": "INSERT INTO player VALUES (2, 'C D', 'C', 'D', 'c d', NULL, NULL, 2)",
    "match_method_enum": "INSERT INTO player_external_id VALUES ('s', 'x', 1, 'guess')",
    "external_id_unique": [
        "INSERT INTO player_external_id VALUES ('s', 'x', 1, 'auto')",
        "INSERT INTO player_external_id VALUES ('s', 'x', 1, 'user')",
    ],
    "season_type_enum": f"{GAME2}'summer', '2026-10-21', 1, 2, 'final')",
    "game_status_enum": f"{GAME2}'regular', '2026-10-21', 1, 2, 'live')",
    "game_same_teams": f"{GAME2}'regular', '2026-10-21', 1, 1, 'final')",
    "minutes_negative": box(minutes=-1),
    "fga_lt_fgm": box(fga=4),
    "fg3m_gt_fgm": box(fg3m=6, fg3a=6),
    "fg3a_lt_fg3m": box(fg3a=0),
    "fg3a_gt_fga": box(fg3a=11),
    "fta_lt_ftm": box(fta=1),
    "reb_sum": box(reb=6),
    "negative_count": box(stl=-1),
    "player_game_unique": [box(), box()],
    "stint_end_before_start": (
        "INSERT INTO player_team_stint VALUES (1, 1, '2026-10-20', '2026-10-01')"
    ),
    "league_capacity_positive": (
        "INSERT INTO fantasy_league VALUES (2, 'lg2', 'L', '2026-27', '9cat_h2h', 0)"
    ),
    "league_key_unique": "INSERT INTO fantasy_league VALUES (2, 'lg', 'L', '2026-27', 'x', 10)",
    "manager_unique": "INSERT INTO manager VALUES (2, 1, 'Ann')",
    "fantasy_team_unique": "INSERT INTO fantasy_team VALUES (2, 1, 't.01', 'Other', 1)",
    "roster_slot_enum": "INSERT INTO roster_entry VALUES (1, 1, 1, 'bench', NULL)",
    "roster_one_team_per_league": [
        "INSERT INTO fantasy_team VALUES (2, 1, 't.02', 'Beta', 1)",
        "INSERT INTO roster_entry VALUES (1, 1, 1, 'active', NULL)",
        "INSERT INTO roster_entry VALUES (1, 1, 2, 'active', NULL)",
    ],
    "status_enum": "INSERT INTO player_status VALUES (1, 'yahoo', '2026-10-20', 'GONE')",
    "load_outcome_enum": (
        "INSERT INTO load_run (source, scope, started_at, outcome)"
        " VALUES ('x', '{}', '2026-10-20', 'maybe')"
    ),
    "foreign_key_enforced": "INSERT INTO player_game (game_id, player_id, team_id, minutes, fgm,"
    " fga, fg3m, fg3a, ftm, fta, oreb, dreb, reb, ast, stl, blk, tov, pf, pts)"
    " VALUES (99, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)",
}


def test_migrate_fresh_db(tmp_path):
    from ffmodel.contract.db import get_engine

    eng = get_engine(f"sqlite:///{tmp_path}/fresh.sqlite")
    assert migrate(eng) == [1]
    assert current_version(eng) == 1
    assert migrate(eng) == []


def test_migration_matches_contract():
    assert MIGRATION.read_text() == CONTRACT_DDL.read_text()


def test_base_rows_are_valid(engine):
    with engine.begin() as conn:
        for stmt in BASE_ROWS:
            conn.execute(text(stmt))
        conn.execute(text(box()))


@pytest.mark.parametrize("name", sorted(VIOLATIONS))
def test_constraint_rejects(engine, name):
    stmts = VIOLATIONS[name]
    stmts = stmts if isinstance(stmts, list) else [stmts]
    with engine.connect() as conn:
        for stmt in BASE_ROWS:
            conn.execute(text(stmt))
        with pytest.raises(IntegrityError):
            for stmt in stmts:
                conn.execute(text(stmt))
        conn.rollback()
