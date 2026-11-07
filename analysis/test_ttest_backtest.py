"""Tests for ttest_backtest. Run from analysis/: uv run --with pytest pytest test_ttest_backtest.py"""

import numpy as np

import ttest_backtest as tb


def test_weights_window_season_and_recency():
    assert tb.weights(5, 3, "window", 3).tolist() == [1, 1, 1, 0, 0, 0, 0, 0]
    assert tb.weights(2, 3, "season", None).tolist() == [1, 1, 0, 0, 0]
    w = tb.weights(2, 2, "weighted", 1)
    assert np.allclose(w, [1, 0.5, 0.25 * 0.25, 0.125 * 0.25])


def test_weighted_moments_match_numpy_when_equal():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(20, 3))
    mean, var, n = tb.weighted_moments(x, np.r_[np.ones(15), np.zeros(5)])
    assert np.allclose(mean, x[:15].mean(0)) and np.allclose(var, x[:15].var(0, ddof=1))
    assert n == 15


def test_prediction_t_and_welch_are_calibrated_for_normal_data():
    rng = np.random.default_rng(1)
    p_pred, p_welch = [], []
    for _ in range(4000):
        past, week = rng.normal(10, 3, (30, 1)), rng.normal(10, 3, (3, 1))
        mean, var, n = tb.weighted_moments(past, np.ones(30))
        p_pred.append(tb.prediction_t(week, mean, var, n)[0])
        p_welch.append(tb.welch(week, mean, var, n)[0])
    assert abs((np.array(p_pred) <= 0.05).mean() - 0.05) < 0.012
    assert (np.array(p_welch) <= 0.05).mean() < 0.08


def test_prediction_t_flags_a_shift_and_handles_zero_spread():
    rng = np.random.default_rng(2)
    past = rng.normal(10, 1, (30, 1))
    mean, var, n = tb.weighted_moments(past, np.ones(30))
    assert tb.prediction_t(np.full((3, 1), 14.0), mean, var, n)[0] < 0.001
    zero = np.zeros((10, 1))
    m, v, n = tb.weighted_moments(zero, np.ones(10))
    assert tb.prediction_t(np.zeros((2, 1)), m, v, n)[0] == 1
    assert tb.prediction_t(np.ones((2, 1)), m, v, n)[0] == 0
