from datetime import date, timedelta

from ffmodel.adapters.nba_stats.stints import Stint, derive_stints

START = date(2025, 10, 21)
END = date(2026, 4, 12)
A, B, C = 1, 2, 3


def d(n: int) -> date:
    return START + timedelta(days=n)


def assert_no_overlap(stints):
    for prev, nxt in zip(stints, stints[1:], strict=False):
        assert prev.end_date is not None and prev.end_date < nxt.start_date


def test_one_team_all_season():
    s = derive_stints([(d(0), A), (d(2), A)], START, current_team_id=A)
    assert s == [Stint(A, START, None)]


def test_late_debut_starts_at_season_start():
    s = derive_stints([(d(40), A), (d(42), A)], START, current_team_id=A)
    assert s == [Stint(A, START, None)]


def test_trade():
    s = derive_stints([(d(0), A), (d(10), A), (d(14), B), (d(16), B)], START, current_team_id=B)
    assert s == [Stint(A, START, d(13)), Stint(B, d(14), None)]
    assert_no_overlap(s)


def test_traded_while_injured():
    s = derive_stints([(d(0), A), (d(10), A)], START, current_team_id=B)
    assert s == [Stint(A, START, d(10)), Stint(B, d(11), None)]
    assert_no_overlap(s)


def test_no_appearances():
    assert derive_stints([], START, current_team_id=C) == [Stint(C, START, None)]
    assert derive_stints([], START) == []


def test_released_or_retired():
    s = derive_stints([(d(0), A), (d(30), A)], START, current_team_id=None)
    assert s == [Stint(A, START, d(30))]


def test_older_season_closes_at_season_end():
    s = derive_stints([(d(0), A), (d(14), B)], START, current_team_id=C, season_end=END)
    assert s == [Stint(A, START, d(13)), Stint(B, d(14), END)]
    assert_no_overlap(s)
