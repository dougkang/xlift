"""xLift (expected lift): the weekly category wins a player adds to one team (007 research R1).

DB-free. Inputs are per-period base-stat lines and team totals in `fmt.base_stats` order, plus a
per-category weekly difference spread *s_c* (two teams' weekly values differ by noise with this
SD).

A team's expected weekly category wins against the league are

    W(T_t) = Σ_c Σ_{u≠t} Φ((k_c(T_t) − k_uc) / s_c),

with keys direction-adjusted (`fmt.rank_key`), so larger is always better and equal keys give
0.5 (FR-003). A player's xLift is the change in W from swapping them with the team's weakest
active player (FR-001, FR-002, FR-005).
"""

import numpy as np

from ffmodel.core.scoring import ScoringFormat

__all__ = [
    "expected_wins",
    "phi",
    "score_candidates",
    "score_candidates_by_category",
    "score_own",
    "score_own_by_category",
    "team_keys",
    "weakest",
]

# A zero spread makes win odds a step function rather than dividing by zero.
_MIN_SPREAD = 1e-12


def phi(x: np.ndarray) -> np.ndarray:
    """Standard normal CDF (Abramowitz–Stegun 7.1.26 erf, error < 2e-7), as the rankings
    report computes it."""
    x = np.asarray(x, dtype=float)
    z = np.abs(x) / np.sqrt(2)
    t = 1 / (1 + 0.3275911 * z)
    poly = t * (
        0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))
    )
    erf = 1 - poly * np.exp(-z * z)
    return 0.5 * (1 + np.sign(x) * erf)


def team_keys(T: np.ndarray, fmt: ScoringFormat) -> np.ndarray:
    """Base-stat totals (..., base stats) → direction-adjusted category keys (..., categories).

    Ratios are recomputed from summed makes and attempts (Constitution I)."""
    T = np.asarray(T, dtype=float)
    totals = {s: T[..., i] for i, s in enumerate(fmt.base_stats)}
    for name, fn in fmt.derived_stats.items():
        totals[name] = fn(totals)
    return fmt.rank_key(fmt.category_values(totals))


def _odds(keys: np.ndarray, others: np.ndarray, spread: np.ndarray) -> np.ndarray:
    """Win probability of keys (..., cats) against each row of others: (..., opponents, cats)."""
    s = np.maximum(np.asarray(spread, dtype=float), _MIN_SPREAD)
    z = (keys[..., None, :] - others) / s
    # A missing value (no attempts) is a coin flip rather than a NaN.
    return phi(np.nan_to_num(z, nan=0.0))


def _wins(keys: np.ndarray, others: np.ndarray, spread: np.ndarray) -> np.ndarray:
    """Expected category wins of keys (..., cats) against each row of others (opponents, cats)."""
    return _odds(keys, others, spread).sum(axis=(-2, -1))


def _wins_by_category(keys: np.ndarray, others: np.ndarray, spread: np.ndarray) -> np.ndarray:
    """Expected wins per category of keys (..., cats), summed over the opponents in others."""
    return _odds(keys, others, spread).sum(axis=-2)


def expected_wins(team_idx: int, K: np.ndarray, spread: np.ndarray) -> float:
    """W for team `team_idx` given every team's keys K (teams, cats) (FR-003)."""
    return float(_wins(K[team_idx], np.delete(K, team_idx, axis=0), spread))


def _wins_with(team_idx, T, totals, fmt, spread) -> np.ndarray:
    """W for team `team_idx` if its totals were each row of `totals`; other teams unchanged."""
    others = team_keys(np.delete(np.asarray(T, dtype=float), team_idx, axis=0), fmt)
    return _wins(team_keys(totals, fmt), others, spread)


def weakest(
    team_idx: int, T: np.ndarray, active_lines: np.ndarray, fmt: ScoringFormat, spread
) -> int | None:
    """Index of the active line whose removal (slot left empty) loses the fewest expected wins
    (FR-005). A line of zeros (no projection) loses none, so it is weakest. None if no lines."""
    lines = np.asarray(active_lines, dtype=float)
    if lines.size == 0:
        return None
    zero = np.flatnonzero(~lines.any(axis=1))
    if zero.size:
        return int(zero[0])
    without = _wins_with(team_idx, T, T[team_idx] - lines, fmt, spread)
    return int(np.argmax(without))  # most wins left = least lost


def score_candidates(
    team_idx: int, T: np.ndarray, out_line, candidate_lines, fmt: ScoringFormat, spread
) -> np.ndarray:
    """W(T_t − out + candidate) − W(T_t) for each candidate (FR-001). An empty slot is a zero
    `out_line`."""
    cands = np.asarray(candidate_lines, dtype=float).reshape(-1, T.shape[-1])
    now = _wins_with(team_idx, T, T[team_idx], fmt, spread)
    return _wins_with(team_idx, T, T[team_idx] - out_line + cands, fmt, spread) - now


def score_candidates_by_category(
    team_idx: int, T: np.ndarray, out_line, candidate_lines, fmt: ScoringFormat, spread
) -> np.ndarray:
    """`score_candidates` per category, (candidates, categories) in `fmt.categories` order: the
    change in expected wins in each category, summed over opponents (009 FR-007). Rows sum to
    `score_candidates`."""
    cands = np.asarray(candidate_lines, dtype=float).reshape(-1, T.shape[-1])
    others = team_keys(np.delete(np.asarray(T, dtype=float), team_idx, axis=0), fmt)
    now = _wins_by_category(team_keys(T[team_idx], fmt), others, spread)
    return _wins_by_category(team_keys(T[team_idx] - out_line + cands, fmt), others, spread) - now


def score_own(
    team_idx: int, T: np.ndarray, own_lines, weakest_line, fmt: ScoringFormat, spread
) -> np.ndarray:
    """W(T_t) − W(T_t − own + weakest) for each own active player (FR-002). The weakest player
    scores exactly 0."""
    own = np.asarray(own_lines, dtype=float).reshape(-1, T.shape[-1])
    weak = np.asarray(weakest_line, dtype=float)
    now = _wins_with(team_idx, T, T[team_idx], fmt, spread)
    out = now - _wins_with(team_idx, T, T[team_idx] - own + weak, fmt, spread)
    out[np.all(own == weak, axis=1)] = 0.0
    return out


def score_own_by_category(
    team_idx: int, T: np.ndarray, own_lines, weakest_line, fmt: ScoringFormat, spread
) -> np.ndarray:
    """`score_own` per category, (players, categories) in `fmt.categories` order: the wins in each
    category the team would lose if each own player were replaced by the weakest, summed over
    opponents. Rows sum to `score_own`; the weakest player's row is all zeros."""
    own = np.asarray(own_lines, dtype=float).reshape(-1, T.shape[-1])
    weak = np.asarray(weakest_line, dtype=float)
    others = team_keys(np.delete(np.asarray(T, dtype=float), team_idx, axis=0), fmt)
    now = _wins_by_category(team_keys(T[team_idx], fmt), others, spread)
    out = now - _wins_by_category(team_keys(T[team_idx] - own + weak, fmt), others, spread)
    out[np.all(own == weak, axis=1)] = 0.0
    return out
