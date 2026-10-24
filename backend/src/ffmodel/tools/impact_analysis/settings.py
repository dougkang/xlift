"""Analysis settings and their defaults (data-model.md AnalysisSettings)."""

from dataclasses import dataclass, replace
from datetime import date, timedelta

from ffmodel.core.data import MatchupState

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
    iterations: int = DEFAULT_ITERATIONS
    seed: int = DEFAULT_SEED
    games_per_period: int = GAMES_PER_PERIOD
    # Tactical: derived from the league's current matchup state (005), never chosen by the user.
    opponent_id: int | None = None
    period_start: date | None = None
    period_end: date | None = None
    matchup_as_of: date | None = None

    @property
    def remaining(self) -> tuple[date, date] | None:
        """Tactical remaining-games window: after the matchup's as-of date through the period's
        end (research R2). Empty (start > end) once the period is over."""
        if self.mode != "tactical" or self.matchup_as_of is None or self.period_end is None:
            return None
        return self.matchup_as_of + timedelta(days=1), self.period_end


def normalize(
    s: AnalysisSettings, state: MatchupState | None = None, today: date | None = None
) -> AnalysisSettings:
    """Fill defaults; in tactical mode, take the opponent and period from the matchup state."""
    s = replace(s, as_of=s.as_of or today or date.today())
    if s.mode != "tactical":
        return s
    line = state.lines.get(s.team_id) if state else None
    if line is None:
        return replace(s, opponent_id=None, period_start=None, period_end=None, matchup_as_of=None)
    return replace(
        s,
        opponent_id=line.opponent_id,
        period_start=state.period_start,
        period_end=state.period_end,
        matchup_as_of=state.as_of,
    )
