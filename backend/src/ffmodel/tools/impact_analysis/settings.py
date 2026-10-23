"""Analysis settings and their defaults (data-model.md AnalysisSettings)."""

from dataclasses import dataclass, replace
from datetime import date, timedelta

DEFAULT_WINDOW = 15
DEFAULT_ITERATIONS = 25_000
DEFAULT_SEED = 20261023
GAMES_PER_PERIOD = 3


@dataclass(frozen=True)
class AnalysisSettings:
    league_id: int
    team_id: int
    mode: str = "strategic"
    window: int = DEFAULT_WINDOW
    as_of: date | None = None
    opponent_id: int | None = None
    period_start: date | None = None
    period_end: date | None = None
    iterations: int = DEFAULT_ITERATIONS
    seed: int = DEFAULT_SEED
    games_per_period: int = GAMES_PER_PERIOD


def week_of(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def normalize(s: AnalysisSettings, today: date | None = None) -> AnalysisSettings:
    as_of = s.as_of or today or date.today()
    start, end = s.period_start, s.period_end
    if s.mode == "tactical" and (start is None or end is None):
        week_start, week_end = week_of(as_of)
        start, end = start or week_start, end or week_end
    return replace(s, as_of=as_of, period_start=start, period_end=end)
