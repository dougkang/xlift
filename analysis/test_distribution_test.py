"""Tests for distribution_test: exact under the null, and able to see a real shift.
Run from analysis/: uv run --with pytest pytest test_distribution_test.py"""

import numpy as np

import distribution_test as dt


def test_rank_u_position_and_ties():
    prior = np.array([1.0, 2, 3])
    assert dt.rank_u(prior, 2.5, tie=0.5) == (2 + 0.5) / 4
    assert dt.rank_u(prior, 0.0, tie=0.0) == 0
    assert dt.rank_u(prior, 2.0, tie=1.0) == (1 + 2) / 4


def test_rank_u_rejects_five_percent_under_the_null_even_when_discrete():
    rng = np.random.default_rng(1)
    u = []
    for _ in range(20000):
        draws = rng.poisson(0.6, 21).astype(float)  # blocks-like: mostly ties
        u.append(dt.rank_u(draws[:20], draws[20], rng.random()))
    u = np.array(u)
    assert abs((dt.p_value(u) <= 0.05).mean() - 0.05) < 0.006
    assert abs(u.mean() - 0.5) < 0.01


def test_permutation_u_rejects_five_percent_under_the_null():
    rng = np.random.default_rng(2)
    p = []
    for _ in range(3000):
        games = rng.poisson(5, (33, 1)).astype(float)
        p.append(dt.p_value(dt.permutation_u(games[:30], games[30:], rng, 199))[0])
    assert abs((np.array(p) <= 0.05).mean() - 0.05) < 0.015


def test_permutation_u_sees_a_shift_and_its_direction():
    rng = np.random.default_rng(3)
    prior = rng.normal(20, 2, (40, 1))
    u = dt.permutation_u(prior, rng.normal(30, 2, (3, 1)), rng, 199)
    assert u[0] > 0.97


def test_real_share_is_zero_for_uniform_and_high_for_small_p():
    rng = np.random.default_rng(4)
    assert dt.real_share(rng.random(100000)) < 0.02
    assert dt.real_share(np.r_[rng.random(5000), np.full(5000, 0.001)]) > 0.45


def test_bh_keeps_only_what_survives():
    p = np.array([0.001, 0.009, 0.04, 0.5])
    assert dt.bh_reject(p, 0.05).tolist() == [True, True, False, False]
    assert not dt.bh_reject(np.array([0.2, 0.3])).any()


def test_tiers_and_period():
    assert dt.minutes_tier(10) == "under 15 min" and dt.minutes_tier(33) == "32+ min"
    assert dt.scoring_tier(25) == "25+ pts"
    assert dt.games_tier(19) == "10-19 prior games"
    assert dt.period_of("2025-11-30") == "Oct-Nov" and dt.period_of("2026-03-20") == "final 4 weeks"


def test_lead_teammate_out_flags_the_missing_high_usage_player():
    line = np.zeros((1, len(dt.STATS)))
    high, low = line.copy(), line.copy()
    high[0, dt.S["fga"]] = 20
    low[0, dt.S["fga"]] = 5
    days = [f"2025-11-{d:02d}" for d in range(1, 13)]
    star = dt.Player(np.array(days[:11]), np.repeat(high, 11, 0), np.full(11, 1), np.ones(11, bool), 0)
    mate = dt.Player(np.array(days), np.repeat(low, 12, 0), np.full(12, 1), np.ones(12, bool), 0)
    out = dt.lead_teammate_out({1: star, 2: mate})
    assert (2, days[11]) in out
    assert (1, days[10]) not in out
