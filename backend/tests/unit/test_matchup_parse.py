"""matchups.csv parsing (005 contracts/matchups-csv.md)."""

import pytest

from ffmodel.adapters.matchup_csv.parse import parse_matchups_csv

HEADER = (
    "week,matchup,team_id,team_name,opponent_id,fgm,fga,ftm,fta,tpm,pts,reb,ast,stl,blk,to,"
    "fg_pct_display,ft_pct_display,cat_wins"
)
A = "1,1,t.01,Cats,t.03,82,147,38,52,9,211,74,34,14,11,16,.558,.731,5"
B = "1,1,t.03,Aggies,t.01,68,159,36,47,27,199,68,41,15,10,34,.428,.766,4"


def write(tmp_path, *rows, header=HEADER):
    p = tmp_path / "matchups.csv"
    p.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return p


def kinds(problems):
    return sorted({p.kind for p in problems})


def test_valid_file(tmp_path):
    rows, problems = parse_matchups_csv(write(tmp_path, A, B))
    assert problems == []
    cats = rows[0]
    assert (cats.week, cats.team_key, cats.opponent_key) == (1, "t.01", "t.03")
    assert cats.totals["fg3m"] == 9 and cats.totals["tov"] == 16  # tpm → fg3m, to → tov
    assert set(cats.totals) == {
        "fgm",
        "fga",
        "fg3m",
        "ftm",
        "fta",
        "reb",
        "ast",
        "stl",
        "blk",
        "tov",
        "pts",
    }


def test_missing_column(tmp_path):
    rows, problems = parse_matchups_csv(write(tmp_path, A, header=HEADER.replace(",tpm", "")))
    assert kinds(problems) == ["MISSING"] and "tpm" in problems[0].message


def test_malformed_value(tmp_path):
    _, problems = parse_matchups_csv(write(tmp_path, A.replace(",74,", ",x,"), B))
    assert "MALFORMED" in kinds(problems)


def test_duplicate_team(tmp_path):
    _, problems = parse_matchups_csv(write(tmp_path, A, A, B))
    assert "DUPLICATE" in kinds(problems)


@pytest.mark.parametrize(
    "rows",
    [
        [A.replace("t.03,82", "t.01,82")],  # plays itself
        [A, B.replace("t.01,68", "t.09,68"), "1,2,t.09,X,t.07,0,0,0,0,0,0,0,0,0,0,0,,,0"],
    ],
)
def test_bad_pairing(tmp_path, rows):
    _, problems = parse_matchups_csv(write(tmp_path, *rows))
    assert "BAD_PAIRING" in kinds(problems)


def test_weeks_must_agree(tmp_path):
    _, problems = parse_matchups_csv(write(tmp_path, A, "2" + B[1:]))
    assert "INCONSISTENT" in kinds(problems)


@pytest.mark.parametrize(
    "row",
    [
        A.replace(",82,147,", ",150,147,"),  # fgm > fga
        A.replace(",38,52,", ",60,52,"),  # ftm > fta
        "1,1,t.01,Cats,t.03,5,10,0,0,9,19,1,1,1,1,1,,,0",  # tpm > fgm
        A.replace(",211,", ",212,"),  # pts mismatch
    ],
)
def test_bad_totals(tmp_path, row):
    _, problems = parse_matchups_csv(write(tmp_path, row, B))
    assert "BAD_TOTALS" in kinds(problems)
