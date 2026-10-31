"""Expected category record (010 R2): odds summed, ties counted half in the win %."""

import pytest

from ffmodel.core.sim import ExpectedRecord, Odds, expected_record


def test_sums_each_outcome():
    r = expected_record([Odds(0.7, 0.1, 0.2), Odds(0.2, 0.0, 0.8), Odds(0.5, 0.5, 0.0)])
    assert (r.wins, r.ties, r.losses) == pytest.approx((1.4, 0.6, 1.0))
    assert r.wins + r.losses + r.ties == pytest.approx(3)  # one per category


def test_tie_counts_half():
    assert expected_record([Odds(0.0, 1.0, 0.0)]).win_pct == 0.5
    r = ExpectedRecord(wins=5.0, losses=3.0, ties=1.0)
    assert r.win_pct == pytest.approx(5.5 / 9)


def test_addition_and_empty():
    total = ExpectedRecord(1.0, 2.0, 0.5) + ExpectedRecord(0.5, 0.0, 0.5)
    assert total == ExpectedRecord(1.5, 2.0, 1.0)
    empty = expected_record([])
    assert (empty.wins, empty.losses, empty.ties, empty.win_pct) == (0, 0, 0, 0)


def test_whole_record_adds_up():  # 010 R4
    from ffmodel.core.sim import Record, whole_record

    # Rounding each part alone would give 4-4-0, eight categories; the leftover goes to the
    # part with the largest fraction.
    assert whole_record(ExpectedRecord(3.6405, 4.1455, 1.214)) == Record(4, 4, 1)
    assert whole_record(ExpectedRecord(3.64, 5.15, 0.21)) == Record(4, 5, 0)
    assert whole_record(ExpectedRecord(4.5, 4.5, 0.0)) == Record(5, 4, 0)  # equal fractions: W
    assert whole_record(ExpectedRecord(9.0, 0.0, 0.0)) == Record(9, 0, 0)
    assert whole_record(ExpectedRecord(0.0, 0.0, 0.0)) == Record(0, 0, 0)
