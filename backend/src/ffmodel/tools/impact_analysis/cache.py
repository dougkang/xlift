"""Process-level projection cache (plan Complexity Tracking).

Keyed by everything a fit depends on, including the latest load run, so it never serves stale
data. Moves never refit: they only change which cached projections are used.
"""

from collections import OrderedDict
from collections.abc import Iterable

from sqlalchemy import text

from ffmodel.core.model import PlayerProjection, build_projections
from ffmodel.core.scoring import ScoringFormat

MAX_KEYS = 32
_cache: OrderedDict[tuple, dict[int, PlayerProjection]] = OrderedDict()


def _latest_run(conn) -> int:
    return conn.execute(text("SELECT COALESCE(MAX(run_id), 0) FROM load_run")).scalar_one()


def projections(conn, player_ids: Iterable[int], fmt: ScoringFormat, settings) -> dict:
    period = (settings.period_start, settings.period_end) if settings.mode == "tactical" else None
    key = (
        str(conn.engine.url),
        settings.league_id,
        settings.as_of,
        settings.window,
        settings.mode,
        period,
        fmt.id,
        _latest_run(conn),
    )
    bucket = _cache.get(key)
    if bucket is None:
        bucket = {}
        _cache[key] = bucket
        while len(_cache) > MAX_KEYS:
            _cache.popitem(last=False)
    _cache.move_to_end(key)
    wanted = set(player_ids)
    missing = wanted - bucket.keys()
    if missing:
        bucket.update(
            build_projections(
                conn, missing, fmt, window=settings.window, as_of=settings.as_of, period=period
            )
        )
    return {pid: bucket[pid] for pid in wanted}


def clear() -> None:
    _cache.clear()
    _original.clear()


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
        s.period_start,
        s.period_end,
        s.opponent_id,
        s.seed,
        s.iterations,
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
