from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from ffmodel.core.data.models import GameWindow, PlayerGameLine
from ffmodel.core.model import (
    MeanPrior,
    PlayerProjection,
    RatioPrior,
    availability_rate,
    estimate_prior,
    fit_projection,
    shrink_projection,
)
from ffmodel.core.model.fit import PRIOR_MIN_GAMES, PRIOR_MIN_POOL

STATS = ("fgm", "fga", "ast")


def line(i, fgm, fga, ast):
    return PlayerGameLine(
        game_id=i,
        season_id="2026-27",
        game_date=date(2026, 11, i),
        team="BOS",
        opponent="MIA",
        minutes=30.0,
        fgm=fgm,
        fga=fga,
        fg3m=0,
        fg3a=0,
        ftm=0,
        fta=0,
        oreb=0,
        dreb=0,
        reb=0,
        ast=ast,
        stl=0,
        blk=0,
        tov=0,
        pf=0,
        pts=2 * fgm,
        plus_minus=0,
    )


def window(rows, requested=15):
    games = tuple(line(i + 1, *r) for i, r in enumerate(rows))
    return GameWindow(player_id=1, requested=requested, found=len(games), games=games)


def test_fit_three_games():
    rows = [(5, 10, 2), (7, 14, 4), (6, 12, 6)]
    p = fit_projection(1, window(rows), STATS)
    x = np.array(rows, float)
    np.testing.assert_allclose(p.mean, x.mean(0))
    lam = 5 / 7
    sigma = (1 - lam) * np.cov(x, rowvar=False) + lam * np.diag(np.maximum(x.mean(0), 0.25))
    np.testing.assert_allclose(p.chol @ p.chol.T, sigma, atol=1e-8)
    assert p.is_short and p.games_found == 3


def test_single_game_uses_prior_only():
    p = fit_projection(1, window([(0, 3, 0)]), STATS)
    np.testing.assert_allclose(p.chol @ p.chol.T, np.diag([0.25, 3, 0.25]), atol=1e-8)


def test_two_games_rank_deficient_is_fine():
    p = fit_projection(1, window([(5, 10, 2), (6, 11, 3)]), STATS)
    assert p.chol is not None and np.all(np.isfinite(p.chol))


def test_no_games():
    p = fit_projection(1, window([]), STATS)
    assert p.chol is None and p.is_short and (p.mean == 0).all()


# --- Recency weighting (006) -------------------------------------------------------------------


def game(gid, season, day, fgm, fga, ast):
    return replace(line(1, fgm, fga, ast), game_id=gid, season_id=season, game_date=day)


def games_window(games, requested=82):
    return GameWindow(player_id=1, requested=requested, found=len(games), games=tuple(games))


def test_equal_weights_reduce_to_the_unweighted_fit():
    rows = [(5, 10, 2), (7, 14, 4), (6, 12, 6)]
    plain = fit_projection(1, window(rows), STATS)
    same = fit_projection(1, window(rows), STATS, half_life=None, season_weight=1.0)
    x = np.array(rows, float)
    np.testing.assert_allclose(same.mean, x.mean(0))
    np.testing.assert_allclose(same.chol @ same.chol.T, plain.chol @ plain.chol.T)
    np.testing.assert_allclose(same.mean_stderr, plain.mean_stderr)
    assert same.effective_games == pytest.approx(3.0) and same.n_eff == pytest.approx(3.0)


def test_weighted_fit_by_hand():
    # Most recent first: two games this season, two last season.
    g = [
        game(4, "2026-27", date(2026, 11, 4), 6, 10, 5),
        game(3, "2026-27", date(2026, 11, 2), 4, 12, 3),
        game(2, "2025-26", date(2026, 4, 10), 8, 14, 2),
        game(1, "2025-26", date(2026, 4, 8), 2, 6, 7),
    ]
    p = fit_projection(
        1, games_window(g), STATS, half_life=40, season_weight=0.25, season="2026-27"
    )
    w = 0.5 ** (np.arange(4) / 40) * 0.25 ** np.array([0, 0, 1, 1])
    x = np.array([[6, 10, 5], [4, 12, 3], [8, 14, 2], [2, 6, 7]], float)
    v1, v2 = w.sum(), (w**2).sum()
    mu = w @ x / v1
    cov = (w[:, None] * (x - mu)).T @ (x - mu) / (v1 - v2 / v1)
    n_eff = v1**2 / v2
    lam = 5 / (n_eff - 1 + 5)
    sigma = (1 - lam) * cov + lam * np.diag(np.maximum(mu, 0.25))
    np.testing.assert_allclose(p.mean, mu)
    np.testing.assert_allclose(p.chol @ p.chol.T, sigma, atol=1e-8)
    np.testing.assert_allclose(p.mean_stderr, np.sqrt(np.diag(sigma) / n_eff))
    assert p.effective_games == pytest.approx(n_eff) and p.games_found == 4


def test_a_missed_season_adds_a_season_of_age():
    recent = game(2, "2026-27", date(2026, 11, 2), 10, 10, 0)
    old = game(1, "2024-25", date(2025, 4, 1), 0, 10, 0)  # 2025-26 missed in between
    p = fit_projection(
        1,
        games_window([recent, old]),
        STATS,
        half_life=None,
        season_weight=0.25,
        season="2026-27",
    )
    w_old = 0.25**2
    assert p.mean[0] == pytest.approx(10 / (1 + w_old))


def test_weights_follow_recency_whatever_the_input_order():
    g = [
        game(1, "2026-27", date(2026, 11, 1), 0, 10, 0),
        game(3, "2026-27", date(2026, 11, 3), 10, 10, 0),
        game(2, "2026-27", date(2026, 11, 2), 5, 10, 0),
    ]
    shuffled = fit_projection(1, games_window(g), STATS, half_life=1, season_weight=1.0)
    ordered = fit_projection(
        1,
        games_window(sorted(g, key=lambda x: x.game_date, reverse=True)),
        STATS,
        half_life=1,
        season_weight=1.0,
    )
    w = 0.5 ** np.arange(3)  # newest (10 made) weighs most
    assert shuffled.mean[0] == pytest.approx(w @ np.array([10, 5, 0]) / w.sum())
    np.testing.assert_allclose(shuffled.mean, ordered.mean)


def test_a_one_game_window_ignores_weights():
    p = fit_projection(
        1,
        games_window([game(1, "2025-26", date(2026, 4, 1), 3, 9, 4)]),
        STATS,
        half_life=40,
        season_weight=0.25,
        season="2026-27",
    )
    np.testing.assert_allclose(p.mean, [3, 9, 4])
    assert p.effective_games == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("played", "team", "rate"), [(0, 5, None), (5, 0, 1.0), (6, 10, 0.6), (11, 10, 1.0)]
)
def test_availability(played, team, rate):
    assert availability_rate(played, team) == rate


# --- Mean shrinkage (empirical Bayes) ----------------------------------------------------------
# Stats: 0 = made, 1 = attempts, 2 = a counting stat.


def proj(mean, stderr, games=10):
    mean, stderr = np.array(mean, float), np.array(stderr, float)
    return PlayerProjection(1, games, 15, mean, np.eye(3), stderr)


def test_prior_needs_a_big_enough_pool():
    pool = [proj([4, 8, 2], [0.5, 0.5, 0.5])] * (PRIOR_MIN_POOL - 1)
    assert estimate_prior(pool, [(0, 1)]) is None
    short = [proj([4, 8, 2], [0.5, 0.5, 0.5], games=PRIOR_MIN_GAMES - 1)] * 100
    assert estimate_prior(short, [(0, 1)]) is None  # short windows don't count toward the pool


def test_estimate_prior():
    rng = np.random.default_rng(1)
    att = rng.uniform(5, 15, 60)
    made = att * rng.uniform(0.4, 0.6, 60)
    cnt = rng.uniform(1, 5, 60)
    se = np.full(3, 0.3)
    pool = [proj([m, a, c], se, games=20) for m, a, c in zip(made, att, cnt, strict=True)]
    prior = estimate_prior(pool, [(0, 1)], [(0, 1)])
    mu = np.c_[made, att, cnt]
    np.testing.assert_allclose(prior.mean, mu.mean(0))
    np.testing.assert_allclose(prior.true_var, mu.var(0) - 0.09)
    np.testing.assert_allclose(prior.real_share, (mu.var(0) - 0.09) / mu.var(0))
    (r,) = prior.ratios
    pct, n_att = made / att, att * 20
    tau2 = pct.var() - np.mean(pct * (1 - pct) / n_att)
    assert (r.made, r.attempts) == (0, 1)
    assert r.rate == pytest.approx(made.sum() / att.sum())
    assert r.kappa == pytest.approx(r.rate * (1 - r.rate) / tau2 - 1)
    assert r.real_share == pytest.approx(tau2 / pct.var())
    assert prior.caps == ((0, 1),)


def test_shrink_counting_stat_by_its_sampling_error():
    prior = MeanPrior(np.array([4.0, 8.0, 2.0]), np.array([1.0, 1.0, 1.0]), ())
    p = shrink_projection(proj([4, 8, 6], [0, 0, 1]), prior)
    # w = 1 / (1 + 1) = 0.5: halfway from 6 to the prior's 2.
    assert p.mean[2] == pytest.approx(4.0)
    sure = shrink_projection(proj([4, 8, 6], [0, 0, 0]), prior)
    assert sure.mean[2] == pytest.approx(6.0)  # no sampling error: kept as is


def test_shrink_percentage_by_attempts():
    prior = MeanPrior(
        np.array([4.0, 8.0, 2.0]), np.array([1.0, 1.0, 1.0]), (RatioPrior(0, 1, 0.5, 20.0, 0.6),)
    )
    # 10 games of 9-for-10: 90 makes on 100 attempts, prior worth 20 attempts at 50%.
    p = shrink_projection(proj([9, 10, 2], [0, 0, 0]), prior)
    rate = (90 + 20 * 0.5) / (100 + 20)
    assert p.mean[0] / p.mean[1] == pytest.approx(rate)
    few = shrink_projection(proj([9, 10, 2], [0, 0, 0], games=1), prior)
    assert few.mean[0] / few.mean[1] < rate  # fewer attempts: pulled harder toward 50%


def test_shrink_keeps_subset_constraints_and_fit():
    prior = MeanPrior(np.array([1.0, 1.0, 1.0]), np.array([1.0, 1.0, 1.0]), (), ((2, 0),))
    p0 = proj([1, 8, 3], [0, 0, 0])
    p = shrink_projection(p0, prior)
    assert p.mean[2] <= p.mean[0]
    assert p.chol is p0.chol and p.mean_stderr is p0.mean_stderr
    assert shrink_projection(p0, None) is p0
    empty = PlayerProjection(1, 0, 15, np.zeros(3), None, np.zeros(3))
    assert shrink_projection(empty, prior) is empty


def test_exempt_stats_stay_unshrunk():
    pool = [proj([4 + i % 3, 8, 1 + i % 4], [0.5, 0.5, 0.5], games=20) for i in range(40)]
    prior = estimate_prior(pool, exempt=[2])
    assert prior.exempt == (2,)
    p0 = proj([9, 8, 6], [1.0, 1.0, 1.0])
    p = shrink_projection(p0, prior)
    assert p.mean[2] == 6  # exempt: unchanged
    assert p.mean[0] != 9  # others still shrink


def test_ratio_shrinkage_counts_effective_games():
    base = MeanPrior(
        np.array([4.0, 8.0, 2.0]), np.array([1.0, 1.0, 1.0]), (RatioPrior(0, 1, 0.5, 20.0, 0.6),)
    )
    weighted = replace(proj([9, 10, 2], [0, 0, 0], games=40), effective_games=10.0)
    p = shrink_projection(weighted, base)
    # 10 effective games of 9-for-10: 90 makes on 100 attempts, not 360 on 400.
    assert p.mean[0] / p.mean[1] == pytest.approx((90 + 20 * 0.5) / (100 + 20))
    rng = np.random.default_rng(2)
    pool = [
        replace(proj([m, a, 1], [0.3, 0.3, 0.3], games=40), effective_games=10.0)
        for m, a in zip(rng.uniform(2, 5, 60), rng.uniform(6, 10, 60), strict=True)
    ]
    (r,) = estimate_prior(pool, [(0, 1)]).ratios
    made, att = np.array([q.mean[0] for q in pool]) * 10, np.array([q.mean[1] for q in pool]) * 10
    assert r.rate == pytest.approx(made.sum() / att.sum())


def test_zero_attempts_fall_back_to_the_league_rate():
    for kappa in (20.0, 0.0):
        prior = MeanPrior(
            np.array([4.0, 8.0, 2.0]),
            np.array([1.0, 1.0, 1.0]),
            (RatioPrior(0, 1, 0.45, kappa, 0.6),),
        )
        p = shrink_projection(proj([0, 0, 2], [0, 0, 0]), prior)
        assert np.isfinite(p.mean).all()
        if p.mean[1] > 0:
            assert p.mean[0] / p.mean[1] == pytest.approx(0.45)
