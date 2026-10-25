"""xLift for a scenario. Moved to `ffmodel.core.value.scenario` and `ffmodel.core.cache` so
every tool shares it (009 research R1); re-exported here for Impact Analysis's callers."""

from ffmodel.core.cache import identity, league_spread
from ffmodel.core.value.scenario import (
    SPREAD_ITERATIONS,
    SPREAD_SEED,
    lines,
    out_line,
    score_pool,
    score_rows,
    team_totals,
    weekly_spread,
)

_out_line = out_line

__all__ = [
    "SPREAD_ITERATIONS",
    "SPREAD_SEED",
    "identity",
    "league_spread",
    "lines",
    "out_line",
    "score_pool",
    "score_rows",
    "team_totals",
    "weekly_spread",
]
