import pytest

from ffmodel.tools.impact_analysis.analysis import _area, _areas


def test_area_fraction():
    assert _area([1.0] * 9) == pytest.approx(1.0)
    assert _area([0.0] * 9) == 0.0
    assert _area([0.5] * 9) == pytest.approx(0.25)  # area scales with radius squared


def test_rank_mapping():
    a = _areas([1] * 9, [1.0] * 9, [1.0] * 9, teams=18)
    assert a == {
        "rank": pytest.approx(1.0),
        "average": pytest.approx(1.0),
        "win_rate": pytest.approx(1.0),
    }
    assert _areas([18] * 9, [0.0] * 9, [0.0] * 9, teams=18)["rank"] == 0.0
