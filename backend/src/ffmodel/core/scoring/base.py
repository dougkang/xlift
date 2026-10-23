"""Scoring-format interface (Constitution II, contracts/scoring-format.md).

The simulation engine, tools, and API depend only on this module, never on a concrete format.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Literal

import numpy as np


class UnsupportedFormat(Exception):
    pass


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    kind: Literal["additive", "ratio"]
    stat: str | None = None
    numerator: str | None = None
    denominator: str | None = None
    higher_is_better: bool = True
    decimals: int = 0

    def __post_init__(self):
        if self.kind == "ratio" and not (self.numerator and self.denominator):
            raise ValueError(f"{self.key}: kind=ratio requires a numerator and denominator")
        if self.kind == "additive" and not self.stat:
            raise ValueError(f"{self.key}: kind=additive requires stat")


Totals = Mapping[str, np.ndarray]


@dataclass(frozen=True)
class ScoringFormat:
    id: str
    name: str
    categories: tuple[Category, ...]
    base_stats: tuple[str, ...]
    derived_stats: Mapping[str, Callable[[Totals], np.ndarray]] = field(default_factory=dict)
    # (smaller, larger): after rounding, smaller <= larger is enforced on team totals.
    subset_constraints: tuple[tuple[str, str], ...] = ()

    def category_values(self, totals: Totals) -> np.ndarray:
        cols = []
        for c in self.categories:
            if c.kind == "additive":
                cols.append(np.asarray(totals[c.stat], dtype=float))
            else:
                num = np.asarray(totals[c.numerator], dtype=float)
                den = np.asarray(totals[c.denominator], dtype=float)
                out = np.full(np.broadcast(num, den).shape, np.nan)
                np.divide(num, den, out=out, where=den > 0)
                cols.append(out)
        return np.stack(cols, axis=-1)

    def _direction(self) -> np.ndarray:
        return np.array([1.0 if c.higher_is_better else -1.0 for c in self.categories])

    def compare(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        diff = (a - b) * self._direction()
        out = np.sign(np.nan_to_num(diff, nan=0.0))
        return out.astype(np.int8)

    def matchup(self, outcomes: np.ndarray) -> np.ndarray:
        wins = (outcomes > 0).sum(axis=-1)
        losses = (outcomes < 0).sum(axis=-1)
        return np.sign(wins - losses).astype(np.int8)

    def projected_average(self, totals: Totals) -> np.ndarray:
        values = []
        for c in self.categories:
            if c.kind == "additive":
                values.append(float(np.mean(totals[c.stat])))
            else:
                den = float(np.mean(totals[c.denominator]))
                values.append(float(np.mean(totals[c.numerator])) / den if den > 0 else np.nan)
        return np.array(values)

    def rank_key(self, averages: np.ndarray) -> np.ndarray:
        """Larger is better, per category, so ranking code never sees direction."""
        return averages * self._direction()


_REGISTRY: dict[str, ScoringFormat] = {}


def register(fmt: ScoringFormat) -> ScoringFormat:
    _REGISTRY[fmt.id] = fmt
    return fmt


def get_format(format_id: str) -> ScoringFormat:
    try:
        return _REGISTRY[format_id]
    except KeyError:
        raise UnsupportedFormat(format_id) from None


def available_formats() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
