"""Process-level projection cache (plan Complexity Tracking).

Keyed by everything a fit depends on, including the latest load run, so it never serves stale
data. Moves never refit: they only change which cached projections are used.
"""

from collections import OrderedDict
from collections.abc import Iterable

from sqlalchemy import text

from ffmodel.core.model import (
    MeanPrior,
    PlayerProjection,
    build_prior,
    build_projections,
    prior_pool_windows,
)
from ffmodel.core.scoring import ScoringFormat

MAX_KEYS = 32
_cache: OrderedDict[tuple, dict[int, PlayerProjection]] = OrderedDict()
# Mean prior per key: built once, so every projection in a bucket shrinks toward the same prior.
_priors: dict[tuple, MeanPrior | None] = {}


def _latest_run(conn) -> int:
    return conn.execute(text("SELECT COALESCE(MAX(run_id), 0) FROM load_run")).scalar_one()


def _projection_key(conn, fmt: ScoringFormat, settings) -> tuple:
    return (
        str(conn.engine.url),
        settings.league_id,
        settings.as_of,
        settings.window,
        settings.mode,
        settings.remaining,  # tactical remaining-games window; None in strategic
        fmt.id,
        _latest_run(conn),
    )


def projections(conn, player_ids: Iterable[int], fmt: ScoringFormat, settings) -> dict:
    period = settings.remaining
    key = _projection_key(conn, fmt, settings)
    bucket = _cache.get(key)
    if bucket is None:
        bucket = {}
        _cache[key] = bucket
        while len(_cache) > MAX_KEYS:
            _priors.pop(_cache.popitem(last=False)[0], None)
    _cache.move_to_end(key)
    wanted = set(player_ids)
    missing = wanted - bucket.keys()
    if missing:
        pool = None
        if key not in _priors:
            # Fetch the pool once: it serves the prior and most requested players' windows.
            pool = prior_pool_windows(conn, window=settings.window, as_of=settings.as_of)
            _priors[key] = build_prior(
                conn, fmt, window=settings.window, as_of=settings.as_of, windows=pool
            )
        bucket.update(
            build_projections(
                conn,
                missing,
                fmt,
                window=settings.window,
                as_of=settings.as_of,
                period=period,
                prior=_priors[key],
                windows=pool,
            )
        )
    return {pid: bucket[pid] for pid in wanted}


def clear() -> None:
    _cache.clear()
    _priors.clear()
    _original.clear()
    _spreads.clear()
    _dab.clear()


# --- dAB (007 research R8) --------------------------------------------------------------------
# Per (database, as-of, load run), extended on demand for new players, like projections.
_dab: OrderedDict[tuple, dict[int, float]] = OrderedDict()


def dab(conn, player_ids: Iterable[int], as_of) -> dict[int, float]:
    from ffmodel.tools.impact_analysis.fragility import dab_values

    key = (str(conn.engine.url), as_of, _latest_run(conn))
    bucket = _dab.get(key)
    if bucket is None:
        bucket = {}
        _dab[key] = bucket
        while len(_dab) > MAX_KEYS:
            _dab.popitem(last=False)
    _dab.move_to_end(key)
    wanted = set(player_ids)
    missing = wanted - bucket.keys()
    if missing:
        bucket.update(dab_values(conn, sorted(missing), as_of))
    return {pid: bucket[pid] for pid in wanted}


# --- Weekly spreads (007 research R2) ---------------------------------------------------------
# League-level and computed from the no-move scenario, so moves reuse them.
_spreads: OrderedDict[tuple, object] = OrderedDict()


def spread(conn, fmt: ScoringFormat, settings, compute):
    """xLift's per-category weekly spread under `settings`; `compute()` on a miss."""
    key = (
        *_projection_key(conn, fmt, settings),
        settings.fragility,
        settings.games_per_period,
    )
    hit = _spreads.get(key)
    if hit is None:
        hit = compute()
        _spreads[key] = hit
        while len(_spreads) > MAX_KEYS:
            _spreads.popitem(last=False)
    _spreads.move_to_end(key)
    return hit


# --- Original analysis (003 research R1) ------------------------------------------------------
# The no-moves analysis depends only on settings and data, so a session of moves computes it once.
ORIGINAL_MAX_KEYS = 8
_original: OrderedDict[tuple, tuple] = OrderedDict()


def original(conn, settings, compute):
    """(result, Computed) for the no-moves scenario under `settings`; `compute()` on a miss."""
    s = settings
    key = (
        str(conn.engine.url),
        s.league_id,
        s.team_id,
        s.mode,
        s.window,
        s.as_of,
        s.remaining,
        s.opponent_id,
        s.seed,
        s.iterations,
        s.fragility,
        s.games_per_period,
        _latest_run(conn),
    )
    hit = _original.get(key)
    if hit is None:
        hit = compute()
        _original[key] = hit
        while len(_original) > ORIGINAL_MAX_KEYS:
            _original.popitem(last=False)
    _original.move_to_end(key)
    return hit
