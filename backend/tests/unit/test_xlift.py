"""xLift core (007 research R1): DB-free, on a synthetic 4-team 9cat league."""

import numpy as np
import pytest

from ffmodel.core.scoring import get_format
from ffmodel.core.value import (
    expected_wins,
    phi,
    score_candidates,
    score_own,
    team_keys,
    weakest,
)

FMT = get_format("9cat_h2h")
STATS = FMT.base_stats  # fgm fga fg3m ftm fta reb ast stl blk tov
CATS = [c.key for c in FMT.categories]


def line(fgm=10, fga=20, fg3m=3, ftm=4, fta=5, reb=8, ast=5, stl=1, blk=1, tov=2):
    return np.array([fgm, fga, fg3m, ftm, fta, reb, ast, stl, blk, tov], dtype=float)


def league():
    rng = np.random.default_rng(7)
    rosters = [
        np.array([line() * rng.uniform(0.6, 1.4, len(STATS)) for _ in range(3)]) for _ in range(4)
    ]
    for r in rosters:
        r[:, 1] = np.maximum(r[:, 1], r[:, 0] + 1)  # fga > fgm
        r[:, 4] = np.maximum(r[:, 4], r[:, 3] + 1)  # fta > ftm
    return rosters, np.array([r.sum(axis=0) for r in rosters])


SPREAD = np.ones(len(CATS)) * 3.0
SPREAD[CATS.index("fg_pct")] = SPREAD[CATS.index("ft_pct")] = 0.03


def test_phi_matches_normal_cdf():
    from statistics import NormalDist

    xs = np.linspace(-4, 4, 41)
    assert np.allclose(phi(xs), [NormalDist().cdf(x) for x in xs], atol=2e-7)


def test_equal_keys_give_half_a_win_per_opponent():
    T = np.array([line()] * 4)
    K = team_keys(T, FMT)
    assert expected_wins(0, K, SPREAD) == pytest.approx(0.5 * 3 * len(CATS))


def test_fewer_turnovers_raise_expected_wins():
    T = np.array([line()] * 4)
    fewer = T.copy()
    fewer[0, STATS.index("tov")] -= 1
    assert expected_wins(0, team_keys(fewer, FMT), SPREAD) > expected_wins(
        0, team_keys(T, FMT), SPREAD
    )


def test_fg_pct_after_swap_is_recomputed_from_makes_and_attempts():
    rosters, T = league()
    out, cand = rosters[0][1], line(fgm=12, fga=18)
    new = T[0] - out + cand
    want = (T[0, 0] - out[0] + cand[0]) / (T[0, 1] - out[1] + cand[1])
    assert team_keys(new, FMT)[CATS.index("fg_pct")] == pytest.approx(want)


def test_weakest_loses_fewest_wins_and_zero_line_is_weakest():
    rosters, T = league()
    w = weakest(0, T, rosters[0], FMT, SPREAD)
    now = expected_wins(0, team_keys(T, FMT), SPREAD)
    lost = []
    for p in rosters[0]:
        moved = T.copy()
        moved[0] -= p
        lost.append(now - expected_wins(0, team_keys(moved, FMT), SPREAD))
    assert w == int(np.argmin(lost))
    with_zero = np.vstack([rosters[0], np.zeros(len(STATS))])
    assert weakest(0, T, with_zero, FMT, SPREAD) == 3
    assert weakest(0, T, np.zeros((0, len(STATS))), FMT, SPREAD) is None


def test_score_own_gives_zero_for_weakest():
    rosters, T = league()
    w = weakest(0, T, rosters[0], FMT, SPREAD)
    vals = score_own(0, T, rosters[0], rosters[0][w], FMT, SPREAD)
    assert vals[w] == 0.0
    # Others: W(T) − W(T − own + weakest). Ratios make this non-additive, so a player can score
    # below a second copy of the weakest (negative); the value is still the swap's effect.
    now = expected_wins(0, team_keys(T, FMT), SPREAD)
    for i, p in enumerate(rosters[0]):
        moved = T.copy()
        moved[0] = T[0] - p + rosters[0][w]
        assert vals[i] == pytest.approx(now - expected_wins(0, team_keys(moved, FMT), SPREAD))


def test_candidate_matches_wins_after_swap():
    rosters, T = league()
    out, cand = rosters[0][0], line(reb=20, blk=4)
    got = score_candidates(0, T, out, cand, FMT, SPREAD)[0]
    moved = T.copy()
    moved[0] = T[0] - out + cand
    want = expected_wins(0, team_keys(moved, FMT), SPREAD) - expected_wins(
        0, team_keys(T, FMT), SPREAD
    )
    assert got == pytest.approx(want)


def test_empty_slot_candidate_uses_zero_out_line():
    rosters, T = league()
    cand = line()
    zero = score_candidates(0, T, np.zeros(len(STATS)), cand, FMT, SPREAD)[0]
    moved = T.copy()
    moved[0] = T[0] + cand
    want = expected_wins(0, team_keys(moved, FMT), SPREAD) - expected_wins(
        0, team_keys(T, FMT), SPREAD
    )
    assert zero == pytest.approx(want) and zero > 0


def test_deterministic():
    rosters, T = league()
    cands = np.array([line(), line(stl=3), line(ast=10)])
    a = score_candidates(1, T, rosters[1][0], cands, FMT, SPREAD)
    b = score_candidates(1, T, rosters[1][0], cands, FMT, SPREAD)
    assert np.array_equal(a, b)
