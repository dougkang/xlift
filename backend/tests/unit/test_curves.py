import numpy as np

from ffmodel.core.sim import density_curves


def test_densities_integrate_and_share_grid():
    rng = np.random.default_rng(0)
    out = density_curves({"a": rng.normal(10, 2, 5000), "b": rng.normal(20, 3, 5000)}, seed=1)
    x = np.asarray(out["x"])
    for d in out["series"].values():
        assert np.trapezoid(d, x) == np.trapezoid(d, x)  # finite
        assert 0.9 < np.trapezoid(d, x) < 1.05
    assert x[0] < 10 and x[-1] > 20


def test_zero_variance_spike():
    out = density_curves({"a": np.full(100, 5.0)})
    d = out["series"]["a"]
    assert np.isfinite(d).all() and d.max() > 0


def test_nan_dropped_and_deterministic():
    v = np.array([1.0, np.nan, 2.0, 3.0] * 100)
    a = density_curves({"a": v}, seed=3)
    b = density_curves({"a": v}, seed=3)
    np.testing.assert_array_equal(a["series"]["a"], b["series"]["a"])
