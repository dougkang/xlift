from datetime import date

import numpy as np
import pytest

from ffmodel.core.model import MeanPrior, build_prior, build_projections
from ffmodel.core.scoring import get_format
from tests.fixtures import dataset as fx

FMT = get_format("9cat_h2h")


def test_projections_from_fixture(fixture_engine):
    with fixture_engine.connect() as conn:
        p = build_projections(
            conn, [fx.IGGY, fx.DONCIC, fx.DYBANTSA], FMT, window=15, as_of=fx.FIXTURE_TODAY
        )
    assert p[fx.IGGY].availability == 0.5  # 2 played of 4 team finals since his window began
    assert p[fx.DONCIC].games_found == 15 and not p[fx.DONCIC].is_short
    assert p[fx.DYBANTSA].is_short and p[fx.DYBANTSA].games_found == 3


def test_games_remaining(fixture_engine):
    with fixture_engine.connect() as conn:
        p = build_projections(
            conn,
            [fx.IGGY],
            FMT,
            window=15,
            as_of=date(2026, 10, 31),
            period=(date(2026, 10, 31), date(2026, 11, 8)),
        )
    assert p[fx.IGGY].games_remaining == 3


def test_mean_shrinkage_wiring(fixture_engine):
    with fixture_engine.connect() as conn:
        # The fixture's pool is too small for a prior: means stay raw by default.
        assert build_prior(conn, FMT, window=15, as_of=fx.FIXTURE_TODAY) is None
        raw = build_projections(
            conn, [fx.DONCIC], FMT, window=15, as_of=fx.FIXTURE_TODAY, prior=None
        )
        d = len(FMT.base_stats)
        prior = MeanPrior(np.zeros(d), np.full(d, 1e-12), ())  # all noise: shrink to the prior
        shrunk = build_projections(
            conn, [fx.DONCIC], FMT, window=15, as_of=fx.FIXTURE_TODAY, prior=prior
        )
    assert raw[fx.DONCIC].mean.sum() > 0
    np.testing.assert_allclose(shrunk[fx.DONCIC].mean, 0, atol=1e-6)
    assert shrunk[fx.DONCIC].availability == raw[fx.DONCIC].availability


def test_blocks_exemption_comes_from_the_format(fixture_engine, monkeypatch):
    # The fixture's pool is small; lower the minimum so a real prior is built from it.
    monkeypatch.setattr("ffmodel.core.model.fit.PRIOR_MIN_POOL", 2)
    with fixture_engine.connect() as conn:
        prior = build_prior(conn, FMT, window=82, as_of=fx.FIXTURE_TODAY)
    assert prior is not None
    assert prior.exempt == (FMT.base_stats.index("blk"),)


def test_prior_does_not_depend_on_the_request(fixture_engine, monkeypatch):
    monkeypatch.setattr("ffmodel.core.model.fit.PRIOR_MIN_POOL", 2)
    with fixture_engine.connect() as conn:
        one = build_projections(conn, [fx.DONCIC], FMT, window=82, as_of=fx.FIXTURE_TODAY)
        many = build_projections(
            conn, [fx.DONCIC, fx.IGGY, fx.DYBANTSA], FMT, window=82, as_of=fx.FIXTURE_TODAY
        )
    np.testing.assert_array_equal(one[fx.DONCIC].mean, many[fx.DONCIC].mean)


# Availability before 006, recorded from the pre-feature code at window 15 (006 SC-004).
AVAILABILITY_BEFORE = {
    fx.IGGY: 0.5,
    fx.DONCIC: 1.0,
    fx.DYBANTSA: 0.75,
    fx.NAW: 2 / 3,
    fx.BUTLER: 0.75,
    fx.PORTIS: 0.5,
}


def test_availability_is_unchanged_by_the_lookback(fixture_engine):
    ids = list(AVAILABILITY_BEFORE)
    with fixture_engine.connect() as conn:
        short = build_projections(conn, ids, FMT, window=15, as_of=fx.FIXTURE_TODAY, prior=None)
        long = build_projections(conn, ids, FMT, window=82, as_of=fx.FIXTURE_TODAY, prior=None)
    for pid, before in AVAILABILITY_BEFORE.items():
        assert short[pid].availability == pytest.approx(before)
        assert long[pid].availability == pytest.approx(before)


def test_prefetched_windows_give_identical_projections(fixture_engine, monkeypatch):
    # The cache passes the prior's pool windows through; results must not change (006 SC-006).
    from ffmodel.core.model import prior_pool_windows

    monkeypatch.setattr("ffmodel.core.model.fit.PRIOR_MIN_POOL", 2)
    ids = [fx.DONCIC, fx.IGGY, fx.DYBANTSA]
    with fixture_engine.connect() as conn:
        fresh = build_projections(conn, ids, FMT, window=82, as_of=fx.FIXTURE_TODAY)
        pool = prior_pool_windows(conn, window=82, as_of=fx.FIXTURE_TODAY)
        prior = build_prior(conn, FMT, window=82, as_of=fx.FIXTURE_TODAY, windows=pool)
        reused = build_projections(
            conn, ids, FMT, window=82, as_of=fx.FIXTURE_TODAY, prior=prior, windows=pool
        )
    for pid in ids:
        np.testing.assert_array_equal(fresh[pid].mean, reused[pid].mean)
        assert fresh[pid].availability == reused[pid].availability
