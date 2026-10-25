"""Database-free player model: recency-weighted joint-normal fit, mean shrinkage and
availability (research R1, R4).

The simulation engine depends only on this module, so it stays importable and testable
without any database (Constitution VII).
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # type-only: importing ffmodel.core.data would load the database layer
    from ffmodel.core.data.models import GameWindow

SHRINK_K = 5
PRIOR_FLOOR = 0.25
JITTER = 1e-9
# Recency weighting (006 research R1): a game j games ago weighs 0.5^(j / RECENCY_HALF_LIFE), times
# SEASON_WEIGHT for each season of age. Backtested against the next 15, 30 and 60 games played.
RECENCY_HALF_LIFE = 40.0
SEASON_WEIGHT = 0.25


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
    effective_games: float | None = None  # (Σw)² / Σw² for a weighted fit; None: games_found

    @property
    def is_short(self) -> bool:
        return self.games_found < self.games_requested

    @property
    def n_eff(self) -> float:
        return float(self.games_found if self.effective_games is None else self.effective_games)


def _start_year(season_id: str) -> int:
    return int(season_id[:4])


def fit_projection(
    player_id: int,
    window: "GameWindow",
    base_stats: Sequence[str],
    *,
    shrink_k: int = SHRINK_K,
    half_life: float | None = None,
    season_weight: float = 1.0,
    season: str | None = None,
) -> PlayerProjection:
    """Joint-normal fit over the window's games (most recent first).

    With `half_life` (games) and `season_weight`, the game j games ago weighs
    0.5^(j / half_life) × season_weight^age, where age is the number of seasons before `season`
    (default: the most recent game's season). The weighted mean and covariance replace the plain
    ones, and the effective sample size (Σw)² / Σw² replaces n in the covariance shrinkage and
    the fit error. The defaults weigh every game equally.
    """
    d = len(base_stats)
    n = window.found
    if n == 0:
        zeros = np.zeros(d)
        return PlayerProjection(player_id, 0, window.requested, zeros, None, zeros)
    games = sorted(window.games, key=lambda g: (g.game_date, g.game_id), reverse=True)
    x = np.array([[getattr(g, s) for s in base_stats] for g in games], dtype=float)
    now = _start_year(season or games[0].season_id)
    age = np.array([now - _start_year(g.season_id) for g in games], dtype=float)
    w = season_weight**age
    if half_life:
        w = w * 0.5 ** (np.arange(n) / half_life)
    v1, v2 = w.sum(), (w**2).sum()
    n_eff = v1**2 / v2
    mu = w @ x / v1
    denom = v1 - v2 / v1  # n − 1 for equal weights, so this is np.cov when unweighted
    dx = x - mu
    sample = (w[:, None] * dx).T @ dx / denom if n > 1 and denom > 0 else np.zeros((d, d))
    prior = np.diag(np.maximum(mu, PRIOR_FLOOR))
    lam = shrink_k / (max(n_eff - 1, 0) + shrink_k)
    sigma = (1 - lam) * sample + lam * prior
    chol = np.linalg.cholesky(sigma + JITTER * np.eye(d))
    stderr = np.sqrt(np.diag(sigma) / n_eff)
    return PlayerProjection(
        player_id, n, window.requested, mu, chol, stderr, effective_games=float(n_eff)
    )


PRIOR_MIN_GAMES = 5  # pool players need this many games in the window to inform the prior
PRIOR_MIN_POOL = 30  # below this, the prior is too unstable to use: no mean shrinkage
RATIO_MIN_ATTEMPTS = 10


@dataclass(frozen=True)
class RatioPrior:
    """Beta-binomial prior on one percentage: `rate`, worth `kappa` attempts."""

    made: int  # base-stat index
    attempts: int
    rate: float
    kappa: float
    real_share: float  # share of the pool's spread in rates that isn't sampling error


@dataclass(frozen=True, eq=False)
class MeanPrior:
    """Empirical-Bayes prior on per-game means, estimated from a pool of raw fits.

    Counting stats shrink toward `mean` by how much of the pool's spread is sampling error;
    each ratio shrinks its rate per its RatioPrior.
    """

    mean: np.ndarray  # m_s
    true_var: np.ndarray  # tau_s^2: pool spread that isn't sampling error
    ratios: tuple[RatioPrior, ...] = ()
    caps: tuple[tuple[int, int], ...] = ()  # (smaller idx, larger idx): smaller <= larger
    real_share: np.ndarray | None = None  # tau_s^2 / pool variance (diagnostic)
    exempt: tuple[int, ...] = ()  # base-stat indices left unshrunk


def estimate_prior(
    fits: Sequence[PlayerProjection],
    ratio_pairs: Sequence[tuple[int, int]] = (),
    caps: Sequence[tuple[int, int]] = (),
    exempt: Sequence[int] = (),
) -> MeanPrior | None:
    pool = [p for p in fits if p.games_found >= PRIOR_MIN_GAMES]
    if len(pool) < PRIOR_MIN_POOL:
        return None
    mu = np.array([p.mean for p in pool])
    se = np.array([p.mean_stderr for p in pool])
    n = np.array([p.n_eff for p in pool], dtype=float)
    spread = mu.var(axis=0)
    true_var = np.maximum(spread - (se**2).mean(axis=0), 1e-9)
    ratios = []
    for made, att in ratio_pairs:
        m, a = mu[:, made] * n, mu[:, att] * n
        ok = a >= RATIO_MIN_ATTEMPTS
        if ok.sum() < PRIOR_MIN_POOL:
            continue
        pct = m[ok] / a[ok]
        rate = float(m[ok].sum() / a[ok].sum())
        tau2 = max(float(pct.var() - np.mean(pct * (1 - pct) / a[ok])), 1e-6)
        kappa = max(rate * (1 - rate) / tau2 - 1, 0.0)
        ratios.append(RatioPrior(made, att, rate, kappa, min(tau2 / float(pct.var()), 1.0)))
    share = np.minimum(true_var / np.maximum(spread, 1e-12), 1.0)
    return MeanPrior(mu.mean(axis=0), true_var, tuple(ratios), tuple(caps), share, tuple(exempt))


def shrink_projection(proj: PlayerProjection, prior: MeanPrior | None) -> PlayerProjection:
    """The projection with its mean shrunk toward the prior; covariance and fit error unchanged."""
    if prior is None or proj.games_found == 0:
        return proj
    w = prior.true_var / (prior.true_var + proj.mean_stderr**2)
    mean = prior.mean + w * (proj.mean - prior.mean)
    mean[list(prior.exempt)] = proj.mean[list(prior.exempt)]
    n = proj.n_eff
    for r in prior.ratios:
        # Attempts shrink as a count first; the rate shrinks with the raw window's attempts.
        made, att = proj.mean[r.made] * n, proj.mean[r.attempts] * n
        # No attempts and no prior weight: nothing to go on but the league rate.
        rate = (made + r.kappa * r.rate) / (att + r.kappa) if att + r.kappa > 0 else r.rate
        mean[r.made] = rate * mean[r.attempts]
    for small, big in prior.caps:
        mean[small] = min(mean[small], mean[big])
    return replace(proj, mean=mean)


def availability_rate(games_played: int, team_games: int) -> float | None:
    if games_played == 0:
        return None
    if team_games == 0:
        return 1.0
    return min(1.0, games_played / team_games)
