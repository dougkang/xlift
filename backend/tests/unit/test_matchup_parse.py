"""matchups.csv parsing (005 contracts/matchups-csv.md)."""

from datetime import date

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


def test_latest_week_kept(tmp_path):
    # A snapshot taken the day a week ends holds last week's final rows, then this week's.
    rows, problems = parse_matchups_csv(write(tmp_path, A, B, "2" + A[1:], "2" + B[1:]))
    assert problems == []
    assert [(r.week, r.line_no) for r in rows] == [(2, 4), (2, 5)]


PERIOD_HEADER = HEADER + ",captured_at,week_start,week_end"
STAMP = ",2026-10-26T22:00:58-07:00,2026-10-26,2026-11-02"


def test_period_columns(tmp_path):
    rows, problems = parse_matchups_csv(write(tmp_path, A + STAMP, B + STAMP, header=PERIOD_HEADER))
    assert problems == []
    assert rows[0].period == (date(2026, 10, 26), date(2026, 11, 2))


def test_periods_must_agree(tmp_path):
    other = B + STAMP.replace("11-02", "11-01")
    _, problems = parse_matchups_csv(write(tmp_path, A + STAMP, other, header=PERIOD_HEADER))
    assert "INCONSISTENT" in kinds(problems)


def test_bad_period_date(tmp_path):
    bad = B + STAMP.replace("2026-11-02", "soon")
    _, problems = parse_matchups_csv(write(tmp_path, A + STAMP, bad, header=PERIOD_HEADER))
    assert "MALFORMED" in kinds(problems)


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
