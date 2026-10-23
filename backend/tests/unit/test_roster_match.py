from pathlib import Path

from sqlalchemy import text

from ffmodel.adapters.roster_csv.match import match_rows
from ffmodel.adapters.roster_csv.parse import parse_roster_csv
from tests.fixtures import dataset as fx

ROSTERS = Path(__file__).resolve().parents[1] / "fixtures" / "rosters"


def rows_by_id(name):
    rows, problems = parse_roster_csv(ROSTERS / name)
    assert problems == []
    return rows


def test_valid_file_matches_everyone(fixture_engine):
    rows = rows_by_id("valid.csv")
    with fixture_engine.connect() as conn:
        matches, problems = match_rows(conn, rows, "yahoo")
    assert problems == []
    got = {r.external_id: matches[r.line_no] for r in rows}
    assert got == {
        "y.1": fx.DONCIC,
        "y.3": fx.BUTLER,
        "y.8": fx.IGGY,
        "y.2": fx.NAW,
        "y.9": fx.SCHRODER,
        "y.10": fx.TWIN_LAL,
        "y.5": fx.DYBANTSA,
        "y.4": fx.PORTIS,
    }


def test_user_match_wins_and_auto_is_recomputed(fixture_engine):
    rows = rows_by_id("valid.csv")
    with fixture_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO player_external_id VALUES ('yahoo', 'y.1', :p, 'user')"),
            {"p": fx.FRED},
        )
        conn.execute(
            text("INSERT INTO player_external_id VALUES ('yahoo', 'y.2', :p, 'auto')"),
            {"p": fx.FRED},
        )
        matches, _ = match_rows(conn, rows, "yahoo")
    got = {r.external_id: matches[r.line_no] for r in rows}
    assert got["y.1"] == fx.FRED  # user confirmation beats an exact name match
    assert got["y.2"] == fx.NAW  # a stale auto match is ignored


def test_ambiguous_without_team(fixture_engine):
    rows = rows_by_id("ambiguous.csv")
    with fixture_engine.connect() as conn:
        matches, problems = match_rows(conn, rows, "yahoo")
    assert matches == {}
    assert problems[0].kind == "UNRESOLVED"
    assert f"[{fx.TWIN_LAL}]" in problems[0].message and f"[{fx.TWIN_GSW}]" in problems[0].message


def test_unknown_player_gets_candidates(fixture_engine):
    rows, _ = parse_roster_csv(ROSTERS / "unresolved.csv")
    with fixture_engine.connect() as conn:
        _, problems = match_rows(conn, rows, "yahoo")
    (problem,) = problems
    assert "y.99" in problem.message and "Zed Nobody" in problem.message
    assert problem.message.count("[") == 3
    assert "ffm roster resolve --source yahoo y.99 <player_id>" in problem.message
