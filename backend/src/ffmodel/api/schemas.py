"""Pydantic models: the contract with the frontend (contracts/api.md).

TypeScript types are generated from the OpenAPI schema these produce (`npm run gen:api`).
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

Mode = Literal["strategic", "tactical"]


class DropMove(BaseModel):
    type: Literal["drop"]
    player_id: int
    team_id: int | None = None  # the team the move was made for; defaults to the request team


class AddMove(BaseModel):
    type: Literal["add"]
    player_id: int
    team_id: int | None = None


class SwapMove(BaseModel):
    type: Literal["swap"]
    acquire_id: int
    give_id: int
    team_id: int | None = None


Move = Annotated[DropMove | AddMove | SwapMove, Field(discriminator="type")]


class ScenarioRequest(BaseModel):
    league_id: int
    team_id: int
    mode: Mode = "strategic"
    window: int = Field(15, ge=1, le=82)
    as_of: date | None = None
    opponent_id: int | None = None
    period_start: date | None = None
    period_end: date | None = None
    iterations: int = Field(10_000, ge=1_000, le=50_000)
    seed: int = 20261023
    moves: list[Move] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self):
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        if self.opponent_id is not None and self.opponent_id == self.team_id:
            raise ValueError("opponent_id must differ from team_id")
        return self


class PlayersRequest(ScenarioRequest):
    query: str = ""
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    free_agents_only: bool = False


# --- Leagues -------------------------------------------------------------------------------


class Freshness(BaseModel):
    nba_data_loaded_at: str | None
    roster_as_of: str | None


class LeagueSummary(BaseModel):
    league_id: int
    league_key: str
    name: str
    season_id: str
    scoring_format_id: str
    active_roster_capacity: int
    team_count: int


class TeamSummary(BaseModel):
    team_id: int
    source_team_key: str
    name: str
    manager: str


class LeagueDetail(LeagueSummary):
    teams: list[TeamSummary]
    freshness: Freshness


# --- Analysis ------------------------------------------------------------------------------


class SettingsEcho(BaseModel):
    mode: Mode
    window: int
    as_of: date
    iterations: int
    seed: int
    opponent_id: int | None
    period_start: date | None
    period_end: date | None


class RecordModel(BaseModel):
    wins: int
    losses: int
    ties: int
    unit: Literal["matchups", "categories"]


class Header(BaseModel):
    team_id: int
    team_name: str
    manager: str
    record: RecordModel | None
    matchup_win_probability: float | None = None


class CategoryInfo(BaseModel):
    key: str
    label: str
    decimals: int
    higher_is_better: bool


class RadarSeries(BaseModel):
    team_id: int
    team_name: str
    emphasis: Literal["selected", "opponent", "other"]
    ranks: list[int]


class Radar(BaseModel):
    team_count: int
    series: list[RadarSeries]


class RankRow(BaseModel):
    category: str
    rank: int
    average: float | None
    league_average: float | None
    leader_team_id: int
    leader_name: str
    leader_average: float | None


class DifferenceRow(BaseModel):
    category: str
    selected_average: float | None
    opponent_average: float | None
    difference: float | None
    favors: Literal["selected", "opponent", "even"]


class CategoryTable(BaseModel):
    kind: Literal["ranks", "differences"]
    rows: list[RankRow | DifferenceRow]


CurveRole = Literal["selected", "leader", "next_best", "league_average", "opponent"]


class CurveSeries(BaseModel):
    role: CurveRole
    team_id: int | None
    label: str
    mean: float | None
    density: list[float]


class Curve(BaseModel):
    category: str
    x: list[float]
    series: list[CurveSeries]


class OddsModel(BaseModel):
    win: float
    tie: float
    loss: float


class RecordCounts(BaseModel):
    wins: int
    losses: int
    ties: int


class MatchupModel(BaseModel):
    opponent_id: int
    opponent_name: str
    opponent_manager: str
    matchup: OddsModel
    categories: dict[str, OddsModel]
    category_record: RecordCounts
    result: Literal["win", "loss", "tie"]


class MatchupTotals(BaseModel):
    matchups: RecordCounts
    categories: RecordCounts


class RosterPlayer(BaseModel):
    player_id: int
    name: str
    nba_team: str | None
    positions: list[str]
    slot: Literal["active", "reserve"]
    status: str
    games_found: int
    games_requested: int
    games_remaining: int | None
    footnote_marker: str | None
    moved: bool


class TeamRoster(BaseModel):
    team_id: int
    team_name: str
    manager: str
    open_active_slots: int
    players: list[RosterPlayer]


class Footnote(BaseModel):
    marker: str
    player_id: int
    text: str


class WarningModel(BaseModel):
    code: Literal["OPPONENT_REQUIRED", "NO_GAMES_REMAINING", "UNSUPPORTED_FORMAT"]
    message: str


class AnalysisResult(BaseModel):
    settings: SettingsEcho
    header: Header
    categories: list[CategoryInfo]
    radar: Radar | None
    category_table: CategoryTable | None
    curves: list[Curve]
    matchups: list[MatchupModel]
    matchup_totals: MatchupTotals | None
    rosters: list[TeamRoster]
    footnotes: list[Footnote]
    warnings: list[WarningModel]
    freshness: Freshness


# --- Picker and errors ---------------------------------------------------------------------


class Eligibility(BaseModel):
    can_add: bool
    add_blocked_reason: str | None
    swap_give_options: list[Literal["roster", "free_agent"]]


class PlayerRow(BaseModel):
    player_id: int
    name: str
    nba_team: str | None
    positions: list[str]
    owner_team_id: int | None
    owner_label: str
    status: str
    games_found: int
    games_requested: int
    games_remaining: int | None
    footnote: str | None
    eligibility: Eligibility


class PlayerPage(BaseModel):
    total: int
    players: list[PlayerRow]


class MoveErrorDetail(BaseModel):
    move_index: int
    code: str
    message: str
