"""Impact Analysis's caches (plan Complexity Tracking).

The projection, dAB and spread caches moved to `ffmodel.core.cache` so every tool shares them
(009 research R1); they're re-exported here. The no-moves analysis is Impact Analysis's own.
"""

from collections import OrderedDict

from ffmodel.core import cache as _core
from ffmodel.core.cache import MAX_KEYS, _latest_run, dab, projections, spread
from ffmodel.core.data import list_leagues

__all__ = ["MAX_KEYS", "clear", "dab", "original", "projections", "spread"]


def clear() -> None:
    _core.clear()
    _original.clear()


# --- Original analysis (003 research R1) ------------------------------------------------------
# The no-moves analysis depends only on settings and data, so a session of moves computes it once.
ORIGINAL_MAX_KEYS = 8
_original: OrderedDict[tuple, tuple] = OrderedDict()


def _scoring_format(conn, league_id: int) -> str | None:
    return next(
        (lg.scoring_format_id for lg in list_leagues(conn) if lg.league_id == league_id), None
    )


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
        _scoring_format(conn, s.league_id),  # the standings rule shapes the result (010)
    )
    hit = _original.get(key)
    if hit is None:
        hit = compute()
        _original[key] = hit
        while len(_original) > ORIGINAL_MAX_KEYS:
            _original.popitem(last=False)
    _original.move_to_end(key)
    return hit
