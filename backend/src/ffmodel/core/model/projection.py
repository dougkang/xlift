"""Per-player projections: joint-normal fit, availability, games remaining (research R1, R4, R5)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
from sqlalchemy import text

from ffmodel.core.data import count_team_games_bulk, get_availability, get_last_n_games_bulk
from ffmodel.core.data.models import GameWindow
from ffmodel.core.scoring import ScoringFormat

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
    player_id: int, window: GameWindow, base_stats: Sequence[str], *, shrink_k: int = SHRINK_K
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


def build_projections(
    conn,
    player_ids: Sequence[int],
    fmt: ScoringFormat,
    *,
    window: int,
    as_of: date,
    period: tuple[date, date] | None = None,
) -> dict[int, PlayerProjection]:
    ids = sorted(set(player_ids))
    windows = get_last_n_games_bulk(conn, ids, window, as_of=as_of)
    remaining = (
        count_team_games_bulk(conn, ids, max(as_of, period[0]), period[1], statuses=("scheduled",))
        if period
        else dict.fromkeys(ids, 0)
    )
    out = {}
    for pid in ids:
        w = windows[pid]
        proj = fit_projection(pid, w, fmt.base_stats)
        avail = None
        if w.found:
            start = min(g.game_date for g in w.games)
            if w.found < w.requested:
                # The window holds every game the player has; count misses back to the start of
                # their earliest stint, not just from their first appearance (research R4).
                first_stint = conn.execute(
                    text("SELECT MIN(start_date) FROM player_team_stint WHERE player_id = :p"),
                    {"p": pid},
                ).scalar_one()
                if first_stint:
                    start = min(start, date.fromisoformat(first_stint))
            span = get_availability(conn, pid, start, as_of)
            avail = availability_rate(w.found, span.team_games)
        out[pid] = PlayerProjection(
            proj.player_id,
            proj.games_found,
            proj.games_requested,
            proj.mean,
            proj.chol,
            proj.mean_stderr,
            availability=avail,
            games_remaining=remaining.get(pid, 0),
        )
    return out
