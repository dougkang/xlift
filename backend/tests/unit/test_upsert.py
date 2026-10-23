from sqlalchemy import text

from ffmodel.adapters.common import finish_run, start_run, upsert


def test_upsert_insert_update_noop(engine):
    rows = [
        {"team_id": 1, "abbreviation": "LAL", "city": "LA", "name": "Lakers"},
        {"team_id": 2, "abbreviation": "GSW", "city": "SF", "name": "Warriors"},
    ]
    with engine.begin() as conn:
        assert upsert(conn, "nba_team", ["team_id"], rows) == (2, 0)
        assert upsert(conn, "nba_team", ["team_id"], rows) == (0, 0)
        rows[1]["city"] = "Golden State"
        assert upsert(conn, "nba_team", ["team_id"], rows) == (0, 1)
        assert conn.execute(text("SELECT city FROM nba_team WHERE team_id = 2")).scalar_one() == (
            "Golden State"
        )


def test_load_run_lifecycle(engine):
    run_id = start_run(engine, "x", {"a": 1})
    finish_run(engine, run_id, "succeeded", 3, 1)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM load_run")).mappings().one()
    assert row["outcome"] == "succeeded" and row["rows_inserted"] == 3 and row["finished_at"]
