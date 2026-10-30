"""Monte Carlo engine (research R2, R3). Projection in, samples out; no database access.

Each player draws from its own stream seeded by (seed, player_id, mode), so a roster move
changes only the moved players' draws (common random numbers) and results are reproducible.
"""

import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

import numpy as np

from ffmodel.core.model import PlayerProjection
from ffmodel.core.scoring import ScoringFormat

STRATEGIC, TACTICAL = 1, 2
KSampler = Callable[[PlayerProjection, np.random.Generator, int], np.ndarray]


@dataclass(frozen=True, eq=False)
class TeamSamples:
    team_id: int
    totals: Mapping[str, np.ndarray]  # stat -> (iterations,) team totals


@dataclass(frozen=True)
class Odds:
    win: float
    tie: float
    loss: float


@dataclass(frozen=True)
class MatchupOdds:
    team_id: int
    opponent_id: int
    categories: tuple[Odds, ...]
    matchup: Odds


@dataclass(frozen=True)
class Record:
    wins: int
    losses: int
    ties: int


@dataclass(frozen=True)
class ExpectedRecord:
    """Expected category W-L-T (010 R2): per category, the odds of each outcome, summed."""

    wins: float
    losses: float
    ties: float

    @property
    def win_pct(self) -> float:
        """Standings win %: a tie counts half (Constitution I)."""
        total = self.wins + self.losses + self.ties
        return (self.wins + 0.5 * self.ties) / total if total > 0 else 0.0

    def __add__(self, other: "ExpectedRecord") -> "ExpectedRecord":
        return ExpectedRecord(
            self.wins + other.wins, self.losses + other.losses, self.ties + other.ties
        )


# A typical strategic week: games per player per scoring period, before availability.
GAMES_PER_PERIOD = 3


def strategic_k(games_per_period: int = GAMES_PER_PERIOD) -> KSampler:
    def sample(proj: PlayerProjection, rng: np.random.Generator, iterations: int) -> np.ndarray:
        p = proj.availability or 0.0
        return rng.binomial(games_per_period, p, size=iterations).astype(float)

    return sample


def tactical_k(proj: PlayerProjection, rng: np.random.Generator, iterations: int) -> np.ndarray:
    return np.full(iterations, float(proj.games_remaining))


def simulate_team(
    team_id: int,
    projections: Iterable[PlayerProjection],
    k_sampler: KSampler,
    fmt: ScoringFormat,
    *,
    iterations: int,
    seed: int,
    mode_code: int,
    base: np.ndarray | None = None,
) -> TeamSamples:
    """Monte Carlo team totals. `base` (tactical, 005) is the team's week-to-date totals per base
    stat: a fixed offset added after the simulated remainder is made valid, so clipping never
    eats into real totals (research R3)."""
    d = len(fmt.base_stats)
    raw = np.zeros((iterations, d))
    for proj in projections:
        if proj.chol is None:
            continue
        rng = np.random.default_rng([seed, proj.player_id, mode_code])
        k = k_sampler(proj, rng, iterations)
        z = rng.standard_normal((iterations, d))
        raw += k[:, None] * proj.mean + np.sqrt(k)[:, None] * (z @ proj.chol.T)

    # Validity is applied to team totals, never per player (research R2: no clipping bias).
    team = np.rint(np.clip(raw, 0, None))
    totals = {s: team[:, i] for i, s in enumerate(fmt.base_stats)}
    for small, big in fmt.subset_constraints:
        totals[small] = np.minimum(totals[small], totals[big])
    if base is not None:
        for i, stat in enumerate(fmt.base_stats):
            totals[stat] = totals[stat] + base[i]
    for name, fn in fmt.derived_stats.items():
        totals[name] = fn(totals)
    return TeamSamples(team_id=team_id, totals=totals)


def category_values(samples: TeamSamples, fmt: ScoringFormat) -> np.ndarray:
    return fmt.category_values(samples.totals)


def _odds(outcomes: np.ndarray) -> Odds:
    return Odds(
        win=float(np.mean(outcomes > 0)),
        tie=float(np.mean(outcomes == 0)),
        loss=float(np.mean(outcomes < 0)),
    )


def matchup_odds(
    team_id: int,
    a_values: np.ndarray,
    opponent_id: int,
    b_values: np.ndarray,
    fmt: ScoringFormat,
) -> MatchupOdds:
    outcomes = fmt.compare(a_values, b_values)
    return MatchupOdds(
        team_id=team_id,
        opponent_id=opponent_id,
        categories=tuple(_odds(outcomes[:, i]) for i in range(outcomes.shape[1])),
        matchup=_odds(fmt.matchup(outcomes)),
    )


def projected_averages(samples: TeamSamples, fmt: ScoringFormat) -> np.ndarray:
    return fmt.projected_average(samples.totals)


def ranks(averages: Mapping[int, np.ndarray], fmt: ScoringFormat) -> dict[int, list[int]]:
    """Competition ranking per category (1 = best), with direction applied."""
    keys = {t: np.nan_to_num(fmt.rank_key(a), nan=-np.inf) for t, a in averages.items()}
    out = {}
    for team, key in keys.items():
        out[team] = [
            1 + sum(int(other[i] > key[i]) for other in keys.values()) for i in range(len(key))
        ]
    return out


def record(odds: Iterable[Odds]) -> Record:
    wins = losses = ties = 0
    for o in odds:
        if o.win > 0.5:
            wins += 1
        elif o.loss > 0.5:
            losses += 1
        else:
            ties += 1
    return Record(wins, losses, ties)


def whole_record(r: ExpectedRecord) -> Record:
    """The expected record in whole categories that still add up (010 R4): each part's floor,
    then the categories left over go to the parts with the largest fractions (ties: W, L, T).
    Rounding each part alone could show 4-4-0 for one matchup's 9 categories."""
    parts = (r.wins, r.losses, r.ties)
    n = round(sum(parts))
    out = [math.floor(p) for p in parts]
    by_fraction = sorted(range(3), key=lambda i: (-(parts[i] - out[i]), i))
    for i in by_fraction[: max(n - sum(out), 0)]:
        out[i] += 1
    return Record(*out)


def expected_record(odds: Iterable[Odds]) -> ExpectedRecord:
    """The expected record over categories (each-category standings, 010 R2)."""
    wins = losses = ties = 0.0
    for o in odds:
        wins += o.win
        losses += o.loss
        ties += o.tie
    return ExpectedRecord(wins, losses, ties)
