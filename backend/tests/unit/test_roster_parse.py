from pathlib import Path

from ffmodel.adapters.roster_csv.parse import parse_roster_csv

ROSTERS = Path(__file__).resolve().parents[1] / "fixtures" / "rosters"


def test_parse_cases():
    rows, problems = parse_roster_csv(ROSTERS / "parse_cases.csv")
    assert problems == []
    luka, iggy, butler = rows
    assert luka.positions == "G,FC" and luka.status == "healthy" and luka.slot == "active"
    assert luka.team_name == "🥭 smoothie’s team"
    assert (iggy.status, iggy.slot) == ("IL+", "reserve")
    assert (butler.status, butler.slot) == ("SUSP", "active")


def test_valid_reserve_slots():
    rows, problems = parse_roster_csv(ROSTERS / "valid.csv")
    assert problems == []
    assert {r.external_id for r in rows if r.slot == "reserve"} == {"y.8", "y.5"}


def test_collects_every_problem(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "team_id,player_id,name,positions,nba_team,status,team_name,manager\n"
        "t.01,,No Id,G,LAL,,A,Ann\n"
        "t.01,y.2,Two,G,LAL,XYZ,A,Ann\n"
        "t.01,y.3,Three,G,LAL,,B,Ann\n"
        "t.02,y.4,Four,G,LAL,,C,Bo\n"
    )
    rows, problems = parse_roster_csv(bad)
    assert [p.kind for p in problems] == ["MISSING", "BAD_STATUS", "INCONSISTENT"]
    assert [r.external_id for r in rows] == ["y.4"]


def test_missing_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("team_id,player_id,name\nt.01,y.1,X\n")
    rows, problems = parse_roster_csv(bad)
    assert rows == [] and problems[0].kind == "MISSING"
