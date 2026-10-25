"""League shape per category: places, gaps and a normal-league reference (008 research R2, R3).

DB-free. From each team's projected averages it returns, per category, the teams in place order
and the gaps between consecutive places, with the gap a normally distributed league of the same
size and spread would show (the rankings report's "against null" reference).
"""

from collections.abc import Mapping
from statistics import NormalDist

import numpy as np

from ffmodel.core.scoring import ScoringFormat
from ffmodel.core.sim.engine import ranks

MIN_TEAMS_FOR_GAPS = 3  # below this a spread, and so a null line, means nothing


def null_steps(n: int) -> np.ndarray:
    """Expected gaps between consecutive order statistics of n standard normal draws, best first
    (Blom's approximation, as the rankings report computes it)."""
    z = np.array([NormalDist().inv_cdf((i - 0.375) / (n + 0.25)) for i in range(n, 0, -1)])
    return z[:-1] - z[1:]


def league_shape(averages: Mapping[int, np.ndarray], fmt: ScoringFormat) -> list[dict]:
    """Per category, in `fmt.categories` order:

    - `teams`: [(team_id, place, rank, value)] by place. Place is the competition rank, ties
      broken by team id; teams without a value are left out.
    - `gaps`: [(to_place, gap, null_gap)] for to_place = 1 … N − 1, where gap is the distance
      between places r and r + 1 and null_gap the normal league's; empty when fewer than
      MIN_TEAMS_FOR_GAPS teams have a value.
    """
    team_ranks = ranks(averages, fmt)
    out = []
    for i in range(len(fmt.categories)):
        have = [t for t in averages if np.isfinite(averages[t][i])]
        order = sorted(have, key=lambda t: (team_ranks[t][i], t))
        values = np.array([float(averages[t][i]) for t in order])
        teams = [
            (t, place, team_ranks[t][i], float(v))
            for place, (t, v) in enumerate(zip(order, values, strict=True), start=1)
        ]
        gaps = []
        n = len(order)
        if n >= MIN_TEAMS_FOR_GAPS:
            step = np.abs(np.diff(values))
            nulls = null_steps(n) * float(np.std(values, ddof=1))
            gaps = [(r + 1, float(step[r]), float(nulls[r])) for r in range(n - 1)]
        out.append({"teams": teams, "gaps": gaps})
    return out
