"""Week-to-date matchup totals in scoring terms (005, research R3/R7).

The matchup state stores the contract's fixed stat vocabulary; these helpers map it onto a
scoring format, so the adapter never needs to know the format (Constitution II, VI).
"""

from typing import TYPE_CHECKING

import numpy as np

from ffmodel.core.scoring import ScoringFormat
from ffmodel.core.sim.engine import Record

if TYPE_CHECKING:  # core.sim stays importable without the database layer
    from ffmodel.core.data.models import MatchupLine


class MissingStats(ValueError):
    def __init__(self, names: list[str]):
        super().__init__(f"matchup state lacks {', '.join(names)}")
        self.names = names


def base_vector(line: "MatchupLine", fmt: ScoringFormat) -> np.ndarray:
    """The team's week-to-date totals in `fmt.base_stats` order (the simulation's offset)."""
    missing = [s for s in fmt.base_stats if s not in line.totals]
    if missing:
        raise MissingStats(missing)
    return np.array([line.totals[s] for s in fmt.base_stats], dtype=float)


def actual_values(line: "MatchupLine", fmt: ScoringFormat) -> np.ndarray:
    """Week-to-date category values; ratios are makes ÷ attempts (NaN with no attempts)."""
    base = base_vector(line, fmt)
    totals = {s: np.array([base[i]]) for i, s in enumerate(fmt.base_stats)}
    for name, fn in fmt.derived_stats.items():
        totals[name] = fn(totals)
    return fmt.category_values(totals)[0]


def current_record(a: "MatchupLine", b: "MatchupLine", fmt: ScoringFormat) -> Record:
    """The matchup score so far for `a` against `b`, by category; ties are explicit."""
    out = fmt.compare(actual_values(a, fmt)[None, :], actual_values(b, fmt)[None, :])[0]
    return Record(int((out > 0).sum()), int((out < 0).sum()), int((out == 0).sum()))
