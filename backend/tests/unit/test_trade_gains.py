"""Trade gains (014 research R1): both teams' change in expected weekly wins from a 1-for-1 swap."""

import numpy as np
import pytest

from ffmodel.core.value import expected_wins, team_keys, trade_gains
from tests.unit.test_xlift import CATS, FMT, SPREAD, league, line


def direct(T, a, b, la, lb):
    """W for both teams recomputed from scratch with the swapped rosters."""
    new = T.copy()
    new[a] = T[a] - la + lb
    new[b] = T[b] - lb + la
    K, K_new = team_keys(T, FMT), team_keys(new, FMT)
    return (
        expected_wins(a, K_new, SPREAD) - expected_wins(a, K, SPREAD),
        expected_wins(b, K_new, SPREAD) - expected_wins(b, K, SPREAD),
    )


def test_gains_equal_a_direct_recompute():
    rosters, T = league()
    ga, gb, by_cat = trade_gains(0, 2, T, rosters[0], rosters[2], FMT, SPREAD)
    assert ga.shape == gb.shape == (3, 3) and by_cat.shape == (3, 3, len(CATS))
    for i in range(3):
        for j in range(3):
            want_a, want_b = direct(T, 0, 2, rosters[0][i], rosters[2][j])
            assert ga[i, j] == pytest.approx(want_a, abs=1e-9)
            assert gb[i, j] == pytest.approx(want_b, abs=1e-9)
    np.testing.assert_allclose(by_cat.sum(axis=-1), ga)


def test_trading_identical_players_changes_nothing():
    rosters, T = league()
    same = rosters[0][:1]
    ga, gb, _ = trade_gains(0, 1, T, same, same, FMT, SPREAD)
    assert ga[0, 0] == pytest.approx(0) and gb[0, 0] == pytest.approx(0)


def test_fewer_turnovers_are_a_gain():
    _, T = league()
    tov = CATS.index("tov")
    give, get = line(tov=6), line(tov=1)  # identical except turnovers
    _, _, by_cat = trade_gains(0, 1, T, give[None], get[None], FMT, SPREAD)
    assert by_cat[0, 0, tov] > 0
    assert np.allclose(np.delete(by_cat[0, 0], tov), 0)


def test_complementary_needs_make_a_win_win():
    """A rebounder for a shooter between a team close in rebounds and one close in threes."""
    base = line()
    T = np.array([base * 5 for _ in range(4)], dtype=float)
    T[0, 5] -= 2  # a: a little behind in rebounds
    T[0, 2] += 15  # ...and well ahead in threes
    T[1, 2] -= 2  # b: a little behind in threes
    T[1, 5] += 15  # ...and well ahead in rebounds
    shooter, rebounder = line(fg3m=5, reb=4), line(fg3m=1, reb=10)
    ga, gb, _ = trade_gains(0, 1, T, shooter[None], rebounder[None], FMT, SPREAD)
    assert ga[0, 0] > 0 and gb[0, 0] > 0
