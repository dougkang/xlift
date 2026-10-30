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
    _computed.clear()


# --- Original analysis (003 research R1) ------------------------------------------------------
# The no-moves analysis depends only on settings and data, so a session of moves computes it once.
ORIGINAL_MAX_KEYS = 8
_original: OrderedDict[tuple, tuple] = OrderedDict()


def _scoring_format(conn, league_id: int) -> str | None:
    return next(
        (lg.scoring_format_id for lg in list_leagues(conn) if lg.league_id == league_id), None
    )


def _scenario_key(conn, s) -> tuple:
    """Everything that shapes a scenario's simulation and results, except the focus (011)."""
    return (
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


def original(conn, settings, compute):
    """(result, Computed) for the no-moves scenario under `settings`; `compute()` on a miss.
    The result is rendered with the focus, so the focus is part of the key (011)."""
    key = (*_scenario_key(conn, settings), settings.focus_opponent_id)
    hit = _original.get(key)
    if hit is None:
        hit = compute()
        _original[key] = hit
        while len(_original) > ORIGINAL_MAX_KEYS:
            _original.popitem(last=False)
    _original.move_to_end(key)
    return hit


# --- Simulation internals (011 research R2) ---------------------------------------------------
# Focusing on an opponent only changes what's drawn, so a focus click reuses the scenario's
# simulation instead of running it again.
COMPUTED_MAX_KEYS = 8
_computed: OrderedDict[tuple, object] = OrderedDict()


def computed(conn, settings, moves, compute):
    """The scenario's `Computed` (simulation internals) for `settings` and `moves`, whatever the
    focus; `compute()` on a miss."""
    key = (*_scenario_key(conn, settings), repr(tuple(moves)))
    hit = _computed.get(key)
    if hit is None:
        hit = compute()
        _computed[key] = hit
        while len(_computed) > COMPUTED_MAX_KEYS:
            _computed.popitem(last=False)
    _computed.move_to_end(key)
    return hit
