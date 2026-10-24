"""Database-free player model: joint-normal fit and availability (research R1, R4).

The simulation engine depends only on this module, so it stays importable and testable
without any database (Constitution VII).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # type-only: importing ffmodel.core.data would load the database layer
    from ffmodel.core.data.models import GameWindow

SHRINK_K = 5
PRIOR_FLOOR = 0.25
JITTER = 1e-9


@dataclass(frozen=True, eq=False)
class PlayerProjection:
    player_id: int
    games_found: int
    games_requested: int
    mean: np.ndarray
    chol: np.ndarray | None
    mean_stderr: np.ndarray
    availability: float | None = None
    games_remaining: int = 0

    @property
    def is_short(self) -> bool:
        return self.games_found < self.games_requested


def fit_projection(
    player_id: int, window: "GameWindow", base_stats: Sequence[str], *, shrink_k: int = SHRINK_K
) -> PlayerProjection:
    d = len(base_stats)
    n = window.found
    if n == 0:
        zeros = np.zeros(d)
        return PlayerProjection(player_id, 0, window.requested, zeros, None, zeros)
    x = np.array([[getattr(g, s) for s in base_stats] for g in window.games], dtype=float)
    mu = x.mean(axis=0)
    sample = np.cov(x, rowvar=False) if n > 1 else np.zeros((d, d))
    prior = np.diag(np.maximum(mu, PRIOR_FLOOR))
    lam = shrink_k / (max(n - 1, 0) + shrink_k)
    sigma = (1 - lam) * sample + lam * prior
    chol = np.linalg.cholesky(sigma + JITTER * np.eye(d))
    stderr = np.sqrt(np.diag(sigma) / n)
    return PlayerProjection(player_id, n, window.requested, mu, chol, stderr)


def availability_rate(games_played: int, team_games: int) -> float | None:
    if games_played == 0:
        return None
    if team_games == 0:
        return 1.0
    return min(1.0, games_played / team_games)
