"""Player Analysis settings and leaderboard query (009 data-model.md)."""

from dataclasses import dataclass, replace
from datetime import date

from ffmodel.core.sim import GAMES_PER_PERIOD

DEFAULT_WINDOW = 82
# The Fragility Penalty, with Impact Analysis's options and default (FR-003).
FRAGILITY_OPTIONS = ("none", "last15", "dab", "dab_tag")
DEFAULT_FRAGILITY = "dab_tag"
EVALUATE_FOR = ("team", "league")
POOLS = ("free_agents", "all")  # or a fantasy team id: that team's players


@dataclass(frozen=True)
class PlayerAnalysisSettings:
    """Strategic by definition (research R5): `mode` and `remaining` are fixed so the core caches
    key it like Impact Analysis's strategic mode."""

    league_id: int
    team_id: int
    window: int = DEFAULT_WINDOW
    as_of: date | None = None
    fragility: str = DEFAULT_FRAGILITY
    games_per_period: int = GAMES_PER_PERIOD
    mode: str = "strategic"

    @property
    def remaining(self) -> None:
        return None


@dataclass(frozen=True)
class LeaderboardQuery:
    evaluate_for: str = "team"  # one of EVALUATE_FOR
    pool: str | int = "free_agents"  # one of POOLS, or a team id in the league
    top: int | None = 25  # 10–50 in steps of 5 from the API; None = no limit, for Python callers
    min_games: int = 5  # 1–15


def normalize(s: PlayerAnalysisSettings, today: date | None = None) -> PlayerAnalysisSettings:
    """Fill the as-of date; reject an unknown Fragility Penalty."""
    if s.fragility not in FRAGILITY_OPTIONS:
        raise ValueError(f"unknown fragility option {s.fragility!r}")
    return replace(s, as_of=s.as_of or today or date.today())
