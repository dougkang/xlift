"""Importing matchups.csv as the league's current matchup state (005 US2)."""

import os
import shutil
import time
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

from ffmodel.adapters.matchup_csv.loader import load_matchups
from ffmodel.cli import app
from ffmodel.core.data import get_matchup_state

HEADER = "week,matchup,team_id,team_name,opponent_id,fgm,fga,ftm,fta,tpm,pts,reb,ast,stl,blk,to"
ROWS = [
    "1,1,t.A,Alphas,t.B,40,80,20,25,10,110,60,30,8,6,12",
    "1,1,t.B,Betas,t.A,30,70,18,24,8,86,45,25,6,4,10",
    "1,2,t.C,Gammas,t.D,28,60,12,16,6,74,40,20,5,5,9",
    "1,2,t.D,Deltas,t.C,22,58,10,15,5,59,50,18,7,3,11",
]
CAPTURED = datetime(2026, 11, 18, 23, 19)  # Wednesday night → as of 11-18, week 11-16 – 11-22


def write(tmp_path, rows=ROWS, name="matchups.csv", when=CAPTURED):
    p = tmp_path / name
    p.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    os.utime(p, (when.timestamp(), when.timestamp()))
    return p


def state(engine):
    with engine.connect() as conn:
        return get_matchup_state(conn, 1)


def table_rows(engine):
    with engine.connect() as conn:
        return (
            conn.execute(text("SELECT COUNT(*) FROM matchup_state")).scalar_one(),
            conn.execute(text("SELECT COUNT(*) FROM matchup_team")).scalar_one(),
        )


def test_load_with_dates_from_file(impact_engine, tmp_path):
    summary = load_matchups(impact_engine, write(tmp_path), "impact-league")
    assert summary.outcome == "succeeded", summary.report
    s = state(impact_engine)
    assert s.week == 1
    assert s.as_of == date(2026, 11, 18)  # the file's modified date
    assert (s.period_start, s.period_end) == (date(2026, 11, 16), date(2026, 11, 22))
    assert {t: line.opponent_id for t, line in s.lines.items()} == {1: 2, 2: 1, 3: 4, 4: 3}
    assert s.lines[1].totals["fg3m"] == 10 and s.lines[1].totals["tov"] == 12
    assert summary.details["pairings"] == [("Alphas", "Betas"), ("Deltas", "Gammas")]
    with impact_engine.connect() as conn:
        run = conn.execute(
            text("SELECT source, outcome FROM load_run WHERE run_id = :r"), {"r": summary.run_id}
        ).one()
    assert tuple(run) == ("matchups_csv", "succeeded")


def test_explicit_dates_override(impact_engine, tmp_path):
    load_matchups(
        impact_engine,
        write(tmp_path),
        "impact-league",
        as_of=date(2026, 11, 17),
        period_start=date(2026, 11, 17),
        period_end=date(2026, 11, 23),
    )
    s = state(impact_engine)
    assert (s.as_of, s.period_start, s.period_end) == (
        date(2026, 11, 17),
        date(2026, 11, 17),
        date(2026, 11, 23),
    )


def test_reimport_replaces(impact_engine, tmp_path):
    load_matchups(impact_engine, write(tmp_path), "impact-league")
    newer = [r.replace(",60,30,8,", ",65,30,8,") if r.startswith("1,1,t.A") else r for r in ROWS]
    summary = load_matchups(impact_engine, write(tmp_path, newer, "b.csv"), "impact-league")
    assert summary.outcome == "succeeded"
    assert summary.replaced == 4
    assert table_rows(impact_engine) == (1, 4)
    assert state(impact_engine).lines[1].totals["reb"] == 65


@pytest.mark.parametrize(
    "rows,kind",
    [
        ([*ROWS[:3], ROWS[3].replace("t.D,Deltas", "t.Z,Zetas")], "UNKNOWN TEAM"),
        (ROWS[:2], "MISSING TEAM"),
        ([ROWS[0].replace(",110,", ",111,"), *ROWS[1:]], "BAD TOTALS"),
    ],
)
def test_rejected_writes_nothing(impact_engine, tmp_path, rows, kind):
    summary = load_matchups(impact_engine, write(tmp_path, rows), "impact-league")
    assert summary.outcome == "rejected"
    assert kind in summary.report
    assert table_rows(impact_engine) == (0, 0)


def test_cli(impact_engine, tmp_path, monkeypatch):
    monkeypatch.setenv("FFMODEL_DB_URL", str(impact_engine.url))
    result = CliRunner().invoke(
        app, ["load", "matchups", str(write(tmp_path)), "--league-key", "impact-league"]
    )
    assert result.exit_code == 0, result.output
    assert "week 1  2026-11-16 → 2026-11-22  as of 2026-11-18" in result.output
    assert "Alphas  vs  Betas" in result.output
    bad = write(tmp_path, ROWS[:2], "bad.csv")
    result = CliRunner().invoke(
        app, ["load", "matchups", str(bad), "--league-key", "impact-league"]
    )
    assert result.exit_code == 2


EXPORTS = Path.home() / "dev/ccsv-rumble-page/data"


@pytest.mark.live
def test_real_export(engine, tmp_path, monkeypatch):
    """SC-004: the exporter's real files load (needs a DB with the NBA season loaded)."""
    if not (EXPORTS / "matchups.csv").exists():
        pytest.skip("no exporter data")
    db = tmp_path / "live.sqlite"
    shutil.copy(Path(__file__).resolve().parents[3] / "data" / "ffmodel.sqlite", db)
    monkeypatch.setenv("FFMODEL_DB_URL", f"sqlite:///{db}")
    runner = CliRunner()
    r = runner.invoke(
        app, ["load", "roster", str(EXPORTS / "rosters.csv"), "--league-key", "live-league"]
    )
    assert r.exit_code == 0, r.output
    started = time.monotonic()
    r = runner.invoke(
        app, ["load", "matchups", str(EXPORTS / "matchups.csv"), "--league-key", "live-league"]
    )
    assert r.exit_code == 0, r.output
    assert time.monotonic() - started < 5
    assert r.output.count("  vs  ") == 9
