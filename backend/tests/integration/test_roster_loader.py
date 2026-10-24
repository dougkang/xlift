from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

from ffmodel.cli import app
from ffmodel.core.data import get_free_agents, get_league
from tests.fixtures import dataset as fx
from tests.invariants import assert_contract_invariants

ROSTERS = Path(__file__).resolve().parents[1] / "fixtures" / "rosters"
AS_OF = "2026-10-30"  # after the fixture's own status snapshot (2026-10-29)
DATA_TABLES = [
    "fantasy_league",
    "manager",
    "fantasy_team",
    "roster_entry",
    "player_status",
    "player_external_id",
]


@pytest.fixture
def cli(fixture_engine, monkeypatch):
    monkeypatch.setenv("FFMODEL_DB_URL", str(fixture_engine.url))
    runner = CliRunner()

    def invoke(*args):
        return runner.invoke(app, list(args))

    return invoke


def load(cli, name, *extra):
    return cli(
        "load",
        "roster",
        str(ROSTERS / name),
        "--league-key",
        "cats",
        "--capacity",
        "3",
        "--as-of",
        AS_OF,
        *extra,
    )


def league_id(engine):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT league_id FROM fantasy_league WHERE league_key = 'cats'")
        ).scalar_one()


def snapshot(engine):
    with engine.connect() as conn:
        return {
            t: conn.execute(text(f"SELECT * FROM {t} ORDER BY 1, 2")).all() for t in DATA_TABLES
        }


def test_valid_load_creates_league(cli, fixture_engine):
    result = load(cli, "valid.csv")
    assert result.exit_code == 0, result.output
    with fixture_engine.connect() as conn:
        snap = get_league(conn, league_id(fixture_engine))
        managers = conn.execute(
            text(
                "SELECT m.display_name, COUNT(*) FROM fantasy_team ft JOIN manager m"
                " USING (manager_id) WHERE ft.league_id = :l GROUP BY m.manager_id"
            ),
            {"l": snap.settings.league_id},
        ).all()
        assert_contract_invariants(conn)
    assert [t.source_team_key for t in snap.teams] == ["t.01", "t.02", "t.03"]
    assert sorted(managers) == [("Doug", 1), ("Paul", 2)]  # research R8: one Paul, two teams


def test_auto_matches_recorded(cli, fixture_engine):
    load(cli, "valid.csv")
    with fixture_engine.connect() as conn:
        methods = conn.execute(
            text("SELECT DISTINCT match_method FROM player_external_id WHERE source = 'yahoo'")
        ).all()
    assert methods == [("auto",)]


def test_unresolved_rejects_then_resolve(cli, fixture_engine):
    before = snapshot(fixture_engine)
    result = load(cli, "unresolved.csv")
    assert result.exit_code == 2
    assert "UNRESOLVED" in result.output and "y.99" in result.output
    assert snapshot(fixture_engine) == before
    with fixture_engine.connect() as conn:
        outcome, report = conn.execute(
            text("SELECT outcome, report FROM load_run ORDER BY run_id DESC")
        ).first()
    assert outcome == "rejected" and "row 10" in report and "y.99" in report

    assert cli("roster", "resolve", "--source", "yahoo", "y.99", str(fx.FRED)).exit_code == 0
    assert load(cli, "unresolved.csv").exit_code == 0
    third = load(cli, "unresolved.csv")
    assert third.exit_code == 0 and "UNRESOLVED" not in third.output
    with fixture_engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT match_method FROM player_external_id WHERE external_id = 'y.99'")
            ).scalar_one()
            == "user"
        )
        assert_contract_invariants(conn)


def test_free_agents_exclude_rostered(cli, fixture_engine):
    load(cli, "valid.csv")
    with fixture_engine.connect() as conn:
        agents = {p.player_id for p in get_free_agents(conn, league_id(fixture_engine))}
    rostered = {
        fx.DONCIC,
        fx.BUTLER,
        fx.IGGY,
        fx.NAW,
        fx.SCHRODER,
        fx.TWIN_LAL,
        fx.DYBANTSA,
        fx.PORTIS,
    }
    assert not agents & rostered
    assert fx.FRED in agents


def test_status_snapshot_and_slots(cli, fixture_engine):
    load(cli, "valid.csv")
    with fixture_engine.connect() as conn:
        n = conn.execute(
            text("SELECT COUNT(*) FROM player_status WHERE source = 'yahoo' AND as_of = :d"),
            {"d": AS_OF},
        ).scalar_one()
        snap = get_league(conn, league_id(fixture_engine))
    assert n == 8
    by_name = {r.player.full_name: r for t in snap.teams for r in t.roster}
    assert (by_name["Jimmy Butler III"].slot, by_name["Jimmy Butler III"].status) == ("active", "Q")
    assert (by_name["Iggy Injured"].slot, by_name["Iggy Injured"].status) == ("reserve", "IL")
    assert (by_name["AJ Dybantsa"].slot, by_name["AJ Dybantsa"].status) == ("reserve", "NA")


def test_reload_replaces_rosters(cli, fixture_engine):
    load(cli, "valid.csv")
    assert load(cli, "moved.csv").exit_code == 0
    with fixture_engine.connect() as conn:
        snap = get_league(conn, league_id(fixture_engine))
        assert_contract_invariants(conn)
    teams = {t.source_team_key: {r.player.player_id for r in t.roster} for t in snap.teams}
    assert fx.BUTLER in teams["t.03"] and fx.BUTLER not in teams["t.01"]


@pytest.mark.parametrize(
    ("name", "kinds"),
    [
        ("over_cap.csv", ["OVER CAP"]),
        ("duplicate.csv", ["DUPLICATE"]),
        ("inconsistent_team.csv", ["INCONSISTENT"]),
        ("bad_status.csv", ["BAD STATUS"]),
    ],
)
def test_rejections_write_nothing(cli, fixture_engine, name, kinds):
    before = snapshot(fixture_engine)
    result = load(cli, name)
    assert result.exit_code == 2, result.output
    for kind in kinds:
        assert kind in result.output
    assert snapshot(fixture_engine) == before


def test_identical_reload_changes_nothing(cli, fixture_engine):
    load(cli, "valid.csv")
    before = snapshot(fixture_engine)
    result = cli(
        "--json",
        "load",
        "roster",
        str(ROSTERS / "valid.csv"),
        "--league-key",
        "cats",
        "--capacity",
        "3",
        "--as-of",
        AS_OF,
    )
    assert result.exit_code == 0
    assert snapshot(fixture_engine) == before
    with fixture_engine.connect() as conn:
        last = conn.execute(
            text("SELECT rows_inserted, rows_updated FROM load_run ORDER BY run_id DESC")
        ).first()
    assert tuple(last) == (0, 0)


def test_missing_season_is_rejected(cli):
    result = cli(
        "load",
        "roster",
        str(ROSTERS / "valid.csv"),
        "--league-key",
        "cats",
        "--season",
        "2030-31",
        "--as-of",
        AS_OF,
    )
    assert result.exit_code == 2 and "ffm load nba" in result.output


def test_as_of_default_season():
    from ffmodel.contract.seasons import current_season

    assert current_season(date(2026, 10, 29)) == "2026-27"


def test_as_of_defaults_to_file_modified_date(cli, fixture_engine, tmp_path):
    """005 FR-002a: with no --as-of, the roster's as-of is the file's modified date."""
    import os
    import shutil
    from datetime import datetime

    path = tmp_path / "valid.csv"
    shutil.copy(ROSTERS / "valid.csv", path)
    stamp = datetime(2026, 10, 30, 21, 15).timestamp()
    os.utime(path, (stamp, stamp))
    result = cli("load", "roster", str(path), "--league-key", "cats", "--capacity", "3")
    assert result.exit_code == 0, result.output
    with fixture_engine.connect() as conn:
        dates = (
            conn.execute(text("SELECT DISTINCT as_of FROM player_status WHERE source = 'yahoo'"))
            .scalars()
            .all()
        )
    assert "2026-10-30" in dates
