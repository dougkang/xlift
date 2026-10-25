"""Conformance suite every registered scoring format must pass (Constitution II)."""

import numpy as np
import pytest

from ffmodel.core.scoring import UnsupportedFormat, available_formats, get_format

BOX_COLUMNS = {
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "oreb",
    "dreb",
    "reb",
    "ast",
    "stl",
    "blk",
    "tov",
    "pf",
    "pts",
    "minutes",
}
FORMATS = available_formats()


def totals(fmt, rng, n=200, scale=1.0):
    t = {s: rng.integers(1, 40, n).astype(float) * scale for s in fmt.base_stats}
    for small, big in fmt.subset_constraints:
        t[small] = np.minimum(t[small], t[big])
    for name, fn in fmt.derived_stats.items():
        t[name] = fn(t)
    return t


@pytest.mark.parametrize("fid", FORMATS)
def test_base_stats_are_contract_columns(fid):
    fmt = get_format(fid)
    assert set(fmt.base_stats) <= BOX_COLUMNS
    assert set(fmt.derived_stats) <= BOX_COLUMNS


@pytest.mark.parametrize("fid", FORMATS)
def test_shapes_and_ratios(fid):
    fmt = get_format(fid)
    t = totals(fmt, np.random.default_rng(0))
    values = fmt.category_values(t)
    assert values.shape == (200, len(fmt.categories))
    for i, c in enumerate(fmt.categories):
        if c.kind == "ratio":
            np.testing.assert_array_equal(values[:, i], t[c.numerator] / t[c.denominator])


@pytest.mark.parametrize("fid", FORMATS)
def test_zero_denominator_is_nan_and_tie(fid):
    fmt = get_format(fid)
    ratios = [i for i, c in enumerate(fmt.categories) if c.kind == "ratio"]
    if not ratios:
        pytest.skip("no ratio categories")
    t = totals(fmt, np.random.default_rng(1), n=5)
    for i in ratios:
        c = fmt.categories[i]
        t[c.numerator][:] = 0
        t[c.denominator][:] = 0
    values = fmt.category_values(t)
    assert np.isnan(values[:, ratios]).all()
    other = fmt.category_values(totals(fmt, np.random.default_rng(2), n=5))
    assert (fmt.compare(values, other)[:, ratios] == 0).all()


@pytest.mark.parametrize("fid", FORMATS)
def test_antisymmetry(fid):
    fmt = get_format(fid)
    rng = np.random.default_rng(3)
    a = fmt.category_values(totals(fmt, rng))
    b = fmt.category_values(totals(fmt, rng))
    np.testing.assert_array_equal(fmt.compare(a, b), -fmt.compare(b, a))
    assert (fmt.compare(a, a) == 0).all()


@pytest.mark.parametrize("fid", FORMATS)
def test_direction(fid):
    fmt = get_format(fid)
    n = len(fmt.categories)
    low, high = np.full((1, n), 1.0), np.full((1, n), 2.0)
    out = fmt.compare(high, low)[0]
    for i, c in enumerate(fmt.categories):
        assert out[i] == (1 if c.higher_is_better else -1), c.key


@pytest.mark.parametrize("fid", FORMATS)
def test_matchup_range_and_antisymmetry(fid):
    fmt = get_format(fid)
    rng = np.random.default_rng(4)
    a = fmt.category_values(totals(fmt, rng))
    b = fmt.category_values(totals(fmt, rng))
    m = fmt.matchup(fmt.compare(a, b))
    assert set(np.unique(m)) <= {-1, 0, 1}
    np.testing.assert_array_equal(m, -fmt.matchup(fmt.compare(b, a)))


@pytest.mark.parametrize("fid", FORMATS)
def test_ratio_of_means(fid):
    fmt = get_format(fid)
    ratio = next((c for c in fmt.categories if c.kind == "ratio"), None)
    if ratio is None:
        pytest.skip("no ratio categories")
    t = totals(fmt, np.random.default_rng(5), n=2)
    t[ratio.numerator] = np.array([1.0, 9.0])
    t[ratio.denominator] = np.array([1.0, 19.0])
    avg = fmt.projected_average(t)[fmt.categories.index(ratio)]
    assert avg == pytest.approx(0.5)
    assert np.mean([1 / 1, 9 / 19]) == pytest.approx(0.737, abs=1e-3)


def test_unknown_format():
    with pytest.raises(UnsupportedFormat):
        get_format("unknown")


@pytest.mark.parametrize("fid", FORMATS)
def test_unshrunk_stats_are_base_stats(fid):
    fmt = get_format(fid)
    assert set(fmt.unshrunk_stats) <= set(fmt.base_stats)
