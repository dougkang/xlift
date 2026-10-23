"""Synthetic projections for engine tests (no database)."""

import numpy as np

from ffmodel.core.model import PlayerProjection
from ffmodel.core.scoring import get_format

FMT = get_format("9cat_h2h")
BASE = {
    "fgm": 7,
    "fga": 15,
    "fg3m": 2,
    "ftm": 4,
    "fta": 5,
    "reb": 6,
    "ast": 5,
    "stl": 1,
    "blk": 1,
    "tov": 2,
}


def projection(
    pid,
    scale=1.0,
    *,
    tov_scale=None,
    availability=1.0,
    games_remaining=0,
    means=None,
    sd_frac=0.3,
    found=15,
):
    m = dict(BASE) if means is None else dict(means)
    mean = np.array(
        [
            m[s] * (tov_scale if s == "tov" and tov_scale is not None else scale)
            for s in FMT.base_stats
        ],
        dtype=float,
    )
    sd = np.maximum(mean * sd_frac, 1e-3)
    chol = np.diag(sd)
    return PlayerProjection(
        pid,
        found,
        15,
        mean,
        chol,
        sd / np.sqrt(15),
        availability=availability,
        games_remaining=games_remaining,
    )
