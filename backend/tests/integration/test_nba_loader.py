from datetime import date

import pytest
from sqlalchemy import text

from ffmodel.adapters.nba_stats import loader as nba_loader
from ffmodel.adapters.nba_stats.loader import load_nba
from tests.fixtures.nba_api.fake_client import FakeNbaStatsClient
from tests.invariants import assert_contract_invariants

TODAY = date(2026, 1, 20)  # makes 2025-26 the current season
SEASON = ["2025-26"]
DATA_TABLES = [
    "season",
    "nba_team",
    "nba_team_external_id",
    "player",
    "player_external_id",
    "game",
    "game_external_id",
    "player_game",
    "player_team_stint",
]


def run(engine, client, **kw):
    return load_nba(engine, seasons=SEASON, client=client, today=TODAY, **kw)


def snapshot(engine) -> dict:
    with engine.connect() as conn:
        return {
            t: conn.execute(text(f"SELECT * FROM {t} ORDER BY 1, 2")).all() for t in DATA_TABLES
        }


def count(engine, sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar_one()


def test_first_load(engine):
    fake = FakeNbaStatsClient()
    summary = run(engine, fake)
    assert summary.outcome == "succeeded"
    assert count(engine, "SELECT COUNT(*) FROM nba_team") == 30
    assert count(engine, "SELECT COUNT(*) FROM game") == len(fake.sched)
    assert count(engine, "SELECT COUNT(*) FROM player_game") == len(fake.logs)
    assert count(engine, "SELECT COUNT(*) FROM player") == len({r["PLAYER_ID"] for r in fake.logs})
    with engine.connect() as conn:
        runs = conn.execute(text("SELECT outcome, rows_inserted FROM load_run")).all()
        assert runs == [("succeeded", summary.total_inserted)] and summary.total_inserted > 0
        assert_contract_invariants(conn)


def test_rerun_changes_nothing(engine):
    run(engine, FakeNbaStatsClient())
    before = snapshot(engine)
    second = run(engine, FakeNbaStatsClient())
    assert snapshot(engine) == before
    assert (second.total_inserted, second.total_updated) == (0, 0)
    with engine.connect() as conn:
        last = conn.execute(
            text("SELECT rows_inserted, rows_updated FROM load_run ORDER BY run_id DESC")
        ).first()
    assert tuple(last) == (0, 0)


def test_incremental_requests_overlap_window(engine):
    run(engine, FakeNbaStatsClient(log_days=("2026-01-15",)))
    fake = FakeNbaStatsClient()
    summary = run(engine, fake)
    assert ("game_log", "2025-26", "2026-01-12") in fake.calls
    day2 = sum(1 for r in fake.logs if r["GAME_DATE"] == "2026-01-16")
    assert summary.inserted["player_game"] == day2


def test_stat_correction_updates_one_row(engine):
    run(engine, FakeNbaStatsClient())
    fake = FakeNbaStatsClient()
    fake.logs[0]["PTS"] += 1
    summary = run(engine, fake)
    assert summary.updated.get("player_game") == 1


def test_partial_write_leaves_no_half_game(engine, monkeypatch):
    real = nba_loader.upsert
    calls = {"n": 0}

    def failing(conn, table, keys, rows):
        result = real(conn, table, keys, rows)
        if table == "player_game":
            calls["n"] += 1
            if calls["n"] == 3:
                raise RuntimeError("boom mid-game")
        return result

    monkeypatch.setattr(nba_loader, "upsert", failing)
    with pytest.raises(RuntimeError):
        run(engine, FakeNbaStatsClient())
    with engine.connect() as conn:
        per_game = conn.execute(
            text("SELECT game_id, COUNT(*) FROM player_game GROUP BY game_id")
        ).all()
        outcome, report = conn.execute(text("SELECT outcome, report FROM load_run")).one()
    assert len(per_game) == 2  # games 1 and 2 committed; game 3 rolled back entirely
    assert outcome == "failed" and "boom" in report

    monkeypatch.setattr(nba_loader, "upsert", real)
    fake = FakeNbaStatsClient()
    run(engine, fake)
    assert count(engine, "SELECT COUNT(*) FROM player_game") == len(fake.logs)


def test_traded_player_team_per_game(engine):
    fake = FakeNbaStatsClient()
    day1 = [r for r in fake.logs if r["GAME_DATE"] == "2026-01-15"]
    day2 = [r for r in fake.logs if r["GAME_DATE"] == "2026-01-16"]
    mover = day1[0]
    day2_players = {r["PLAYER_ID"] for r in day2}
    assert mover["PLAYER_ID"] not in day2_players
    other_team_row = next(r for r in day2 if r["TEAM_ID"] != mover["TEAM_ID"])
    traded = dict(other_team_row, PLAYER_ID=mover["PLAYER_ID"], PLAYER_NAME=mover["PLAYER_NAME"])
    fake.logs.append(traded)
    run(engine, fake)
    with engine.connect() as conn:
        teams = conn.execute(
            text(
                "SELECT g.game_date, t.external_id FROM player_game pg"
                " JOIN game g ON g.game_id = pg.game_id"
                " JOIN nba_team_external_id t ON t.team_id = pg.team_id AND t.source = 'nba_stats'"
                " JOIN player_external_id p ON p.player_id = pg.player_id"
                " AND p.source = 'nba_stats'"
                " WHERE p.external_id = :pid ORDER BY g.game_date"
            ),
            {"pid": str(mover["PLAYER_ID"])},
        ).all()
        assert [t for _, t in teams] == [str(mover["TEAM_ID"]), str(traded["TEAM_ID"])]
        assert_contract_invariants(conn)


def test_live_and_postponed_games(engine):
    run(engine, FakeNbaStatsClient())
    with engine.connect() as conn:
        statuses = dict(
            conn.execute(
                text(
                    "SELECT e.external_id, g.status FROM game g"
                    " JOIN game_external_id e USING (game_id)"
                )
            ).all()
        )
        live_boxes = conn.execute(
            text(
                "SELECT COUNT(*) FROM player_game pg JOIN game g USING (game_id)"
                " WHERE g.status <> 'final'"
            )
        ).scalar_one()
    assert statuses["0022500596"] == "scheduled"  # gameStatus 2 (live)
    assert statuses["0022500597"] == "postponed"
    assert statuses["0022500593"] == "scheduled"
    assert live_boxes == 0


def test_external_ids(engine):
    run(engine, FakeNbaStatsClient())
    assert count(
        engine,
        "SELECT COUNT(*) FROM player_external_id WHERE source = 'nba_stats'"
        " AND match_method = 'exact'",
    ) == count(engine, "SELECT COUNT(*) FROM player")
    assert count(engine, "SELECT COUNT(*) FROM game_external_id") == count(
        engine, "SELECT COUNT(*) FROM game"
    )
    assert count(engine, "SELECT COUNT(*) FROM nba_team_external_id") == 30
