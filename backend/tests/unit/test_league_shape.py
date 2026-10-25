"""League shape per category (008 research R2, R3): DB-free, on synthetic averages."""

from statistics import NormalDist

import numpy as np
import pytest

from ffmodel.core.scoring import get_format
from ffmodel.core.sim import league_shape, ranks

FMT = get_format("9cat_h2h")
CATS = [c.key for c in FMT.categories]
PTS, TOV, FT = CATS.index("pts"), CATS.index("tov"), CATS.index("ft_pct")


def averages(seed=3, teams=6):
    rng = np.random.default_rng(seed)
    base = np.array([400, 150, 90, 30, 20, 50, 0.47, 0.78, 50], dtype=float)
    return {t: base * rng.uniform(0.85, 1.15, len(base)) for t in range(1, teams + 1)}


def report_null_gaps(values):
    """The rankings notebook's gap cell, verbatim in substance."""
    n = len(values)
    z = np.array([NormalDist().inv_cdf((i - 0.375) / (n + 0.25)) for i in range(n, 0, -1)])
    return (z[:-1] - z[1:]) * np.std(values, ddof=1)


def test_places_follow_competition_rank_with_team_tiebreak():
    avg = averages()
    avg[4][PTS] = avg[2][PTS]  # a tie
    shape = league_shape(avg, FMT)[PTS]
    r = ranks(avg, FMT)
    assert [p for _, p, _, _ in shape["teams"]] == list(range(1, 7))
    assert [rank for _, _, rank, _ in shape["teams"]] == sorted(r[t][PTS] for t in avg)
    tied = [t for t, _, _, _ in shape["teams"] if t in (2, 4)]
    assert tied == [2, 4]
    for t, _, rank, v in shape["teams"]:
        assert rank == r[t][PTS] and v == pytest.approx(avg[t][PTS])


def test_turnovers_place_fewest_first():
    shape = league_shape(averages(), FMT)[TOV]
    values = [v for *_, v in shape["teams"]]
    assert values == sorted(values)


def test_missing_values_are_left_out():
    avg = averages()
    avg[5][FT] = np.nan
    shape = league_shape(avg, FMT)[FT]
    assert [t for t, *_ in shape["teams"]].count(5) == 0
    assert len(shape["teams"]) == 5 and len(shape["gaps"]) == 4


def test_gaps_and_null_gaps_match_the_report():
    for cat in range(len(CATS)):
        shape = league_shape(averages(), FMT)[cat]
        values = np.array([v for *_, v in shape["teams"]])
        gaps = shape["gaps"]
        assert [r for r, _, _ in gaps] == list(range(1, len(values)))
        assert np.allclose([g for _, g, _ in gaps], np.abs(np.diff(values)))
        assert all(g >= 0 for _, g, _ in gaps)
        assert np.allclose([n for *_, n in gaps], report_null_gaps(values), atol=1e-9)


def test_too_few_teams_gives_no_gaps():
    shape = league_shape(averages(teams=2), FMT)[PTS]
    assert len(shape["teams"]) == 2 and shape["gaps"] == []


def test_equal_values_give_zero_gaps():
    avg = {t: np.full(len(CATS), 1.0) for t in range(1, 5)}
    shape = league_shape(avg, FMT)[PTS]
    assert all(g == 0 and n == 0 for _, g, n in shape["gaps"])
