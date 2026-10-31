"""Pydantic models: the contract with the frontend (contracts/api.md).

TypeScript types are generated from the OpenAPI schema these produce (`npm run gen:api`).
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

Mode = Literal["strategic", "tactical"]
Fragility = Literal["none", "last15", "dab", "dab_tag"]


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
    window: int = Field(82, ge=1, le=82)
    as_of: date | None = None
    # Tactical's opponent and period come from the league's current matchup state (005);
    # older clients that still send opponent_id / period_* have them ignored.
    iterations: int = Field(25_000, ge=1_000, le=50_000)
    seed: int = 20261023
    # Fragility Penalty (007): how availability is estimated for the whole analysis.
    fragility: Fragility = "dab_tag"
    moves: list[Move] = Field(default_factory=list)
    # Strategic: compare with this H2H opponent instead of the league (011); ignored in tactical.
    focus_opponent_id: int | None = None

    @model_validator(mode="after")
    def _focus_is_another_team(self):
        if self.focus_opponent_id is not None and self.focus_opponent_id == self.team_id:
            raise ValueError("focus_opponent_id must be another team")
        return self


class PlayersRequest(ScenarioRequest):
    query: str = ""
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    free_agents_only: bool = False
    # Filters and sort (013); empty = no filter / total xLift.
    positions: list[Literal["G", "F", "C"]] = Field(default_factory=list)
    owners: list[Literal["fa"] | int] = Field(default_factory=list)  # "fa" = free agents
    sort_categories: list[str] = Field(default_factory=list)  # the format's category keys


# --- Leagues -------------------------------------------------------------------------------


class Freshness(BaseModel):
    nba_data_loaded_at: str | None
    roster_as_of: str | None
    matchup_as_of: str | None = None


class CurrentMatchup(BaseModel):
    """The league's imported matchup state (005); null until matchups.csv is loaded."""

    week: int
    period_start: date
    period_end: date
    as_of: date
    loaded_at: str | None


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
    current_matchup: CurrentMatchup | None = None


# --- Analysis ------------------------------------------------------------------------------


class SettingsEcho(BaseModel):
    mode: Mode
    window: int
    as_of: date
    iterations: int
    seed: int
    fragility: Fragility
    opponent_id: int | None
    period_start: date | None
    period_end: date | None
    focus_opponent_id: int | None = None


class RecordModel(BaseModel):
    wins: int
    losses: int
    ties: int
    unit: Literal["matchups", "categories"]


class RecordCounts(BaseModel):
    wins: int
    losses: int
    ties: int


class ExpectedRecordModel(BaseModel):
    """Expected category W-L-T, unrounded (each-category standings, 010)."""

    wins: float
    losses: float
    ties: float
    win_pct: float  # (W + T/2) / (W + L + T)
    record: RecordCounts  # in whole categories, as the page shows it (010 R4)


class CurrentScore(BaseModel):
    wins: int
    losses: int
    ties: int


class MatchupHeader(BaseModel):
    """Tactical: the current matchup (005). `current` is the score from week-to-date totals."""

    opponent_id: int
    opponent_name: str
    week: int
    period_start: date
    period_end: date
    as_of: date
    final: bool
    current: CurrentScore


class Header(BaseModel):
    team_id: int
    team_name: str
    manager: str
    record: RecordModel | None  # null under each-category standings
    expected_record: ExpectedRecordModel | None = None  # each-category standings (010)
    matchup_win_probability: float | None = None
    matchup: MatchupHeader | None = None


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
    # Projected average per category, min-max scaled across the league; 1 = best (direction
    # applied), 0.5 when all teams are equal.
    normalized: list[float]
    # Chance of beating a random league opponent in each category (ties count half).
    win_rate: list[float]
    area: "RadarArea"
    averages: list[float | None]


class RadarArea(BaseModel):
    """Radar area per scale, relative to the league's largest radar (top team = 1.0)."""

    rank: float
    average: float
    win_rate: float


class RadarReference(BaseModel):
    """A league reference shape on the radar (strategic): the League Average."""

    role: Literal["league_average"]
    label: str
    ranks: list[int]
    normalized: list[float]
    win_rate: list[float]


class Radar(BaseModel):
    team_count: int
    series: list[RadarSeries]
    # Strategic only; empty in tactical mode.
    league: list[RadarReference] = []


class RankRow(BaseModel):
    category: str
    rank: int
    average: float | None
    league_average: float | None
    leader_team_id: int
    leader_name: str
    leader_average: float | None
    win_rate: float  # chance of beating a random league opponent in this category


class DifferenceRow(BaseModel):
    category: str
    # Week-to-date values (005); the averages are projected finals (week to date + remaining).
    selected_actual: float | None = None
    opponent_actual: float | None = None
    selected_average: float | None
    opponent_average: float | None
    difference: float | None
    favors: Literal["selected", "opponent", "even"]
    win_probability: float  # chance the selected team wins this category vs the opponent


class CategoryTable(BaseModel):
    kind: Literal["ranks", "differences"]
    rows: list[RankRow | DifferenceRow]


CurveRole = Literal[
    "selected",
    "leader",
    "next_best",
    "league_average",
    "opponent",
    "selected_original",
]


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


class MatchupModel(BaseModel):
    opponent_id: int
    opponent_name: str
    opponent_manager: str
    matchup: OddsModel
    categories: dict[str, OddsModel]
    category_record: RecordCounts
    result: Literal["win", "loss", "tie"] | None  # null under each-category standings
    expected_record: ExpectedRecordModel | None = None  # each-category standings (010)


class MatchupTotals(BaseModel):
    matchups: RecordCounts | None  # null under each-category standings
    categories: RecordCounts
    expected: ExpectedRecordModel | None = None  # each-category standings (010)


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
    # Expected weekly category wins added for this row's own team, against a copy of its
    # weakest active player (007). Reserve players are scored as if active. None without a
    # projection.
    xlift: float | None


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
    code: Literal[
        "NO_GAMES_REMAINING",
        "UNSUPPORTED_FORMAT",
        # Current matchup (005)
        "MATCHUP_NOT_LOADED",
        "MATCHUP_STALE",
        "ROSTER_MATCHUP_DATES_DIFFER",
        "MATCHUP_STATS_MISSING",
    ]
    message: str


# --- Changes vs the original roster (003 contracts/api.md) ---------------------------------


class Change(BaseModel):
    """Signed change rounded to display precision, classified for the selected team."""

    delta: float
    tone: Literal["better", "worse", "neutral"]


class WLTChange(BaseModel):
    wins: Change | None
    losses: Change | None
    ties: Change | None


class HeaderChange(WLTChange):
    chance_to_win: Change | None
    expected_wins: Change | None = None  # each-category standings (010)
    win_pct: Change | None = None  # each-category, strategic


class RadarOriginal(BaseModel):
    team_id: int
    emphasis: Literal["selected", "opponent", "other"]
    ranks: list[int]
    normalized: list[float]
    win_rate: list[float]


ToneOrNone = Literal["better", "worse", "neutral"] | None


class RadarTones(BaseModel):
    rank: list[ToneOrNone]
    average: list[ToneOrNone]
    win_rate: list[ToneOrNone]


class AreaChange(BaseModel):
    rank: Change | None
    average: Change | None
    win_rate: Change | None


class RadarChange(BaseModel):
    original: list[RadarOriginal]
    tones: dict[str, RadarTones]
    area: AreaChange


class CategoryChange(BaseModel):
    # Strategic
    rank: Change | None = None
    average: Change | None = None
    league_average: Change | None = None
    leader_average: Change | None = None
    win_rate: Change | None = None
    # Tactical
    selected_average: Change | None = None
    opponent_average: Change | None = None
    difference: Change | None = None
    win_probability: Change | None = None


class CurveChange(BaseModel):
    means: dict[str, Change | None]


class MatchupChange(BaseModel):
    category_record: WLTChange
    win: Change | None
    original_result: Literal["win", "loss", "tie"] | None  # null under each-category standings
    transition: Literal["flip_better", "flip_worse", "better", "worse"] | None
    expected_wins: Change | None = None  # each-category standings (010)


class TotalsChange(BaseModel):
    matchups: WLTChange | None  # null under each-category standings
    categories: WLTChange
    expected_wins: Change | None = None  # each-category standings (010)


class Changes(BaseModel):
    header: HeaderChange
    radar: RadarChange
    category_table: dict[str, CategoryChange]
    curves: dict[str, CurveChange]
    matchups: dict[str, MatchupChange]
    matchup_totals: TotalsChange | None  # None in tactical (no H2H, 005)


class ShapeTeam(BaseModel):
    """One team in a category's league shape (008)."""

    team_id: int
    team_name: str
    place: int  # 1…N by competition rank, ties broken by team id
    rank: int  # the Per Category Ranking table's rank (ties share it)
    value: float
    selected: bool


class ShapeGap(BaseModel):
    """The gap between places `to_place` and `to_place` + 1, and a normal league's (008)."""

    to_place: int
    gap: float
    null_gap: float
    mark: Literal["climb", "cushion"] | None


class ShapePoint(BaseModel):
    place: int
    rank: int
    value: float


class CategoryShape(BaseModel):
    """Strategic only: every team's place and value in one category, and the gaps (008)."""

    category: str
    teams: list[ShapeTeam]
    gaps: list[ShapeGap]
    before: ShapePoint | None  # the selected team before moves; null without moves


class Focus(BaseModel):
    """The H2H opponent the page is focused on (011)."""

    opponent_id: int
    opponent_name: str


class AnalysisResult(BaseModel):
    settings: SettingsEcho
    # How a matchup enters the standings, from the league's scoring format (010).
    standings: Literal["matchup", "category"] = "matchup"
    header: Header
    categories: list[CategoryInfo]
    radar: Radar | None
    category_table: CategoryTable | None
    curves: list[Curve]
    league_shape: list[CategoryShape] | None = None
    matchups: list[MatchupModel]
    matchup_totals: MatchupTotals | None
    rosters: list[TeamRoster]
    footnotes: list[Footnote]
    warnings: list[WarningModel]
    freshness: Freshness
    changes: Changes | None = None
    focus: Focus | None = None  # strategic, when focused on an H2H opponent (011)


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
    # Expected weekly category wins added for the selected team, swapped in for its weakest
    # active player (007). None without a projection.
    xlift: float | None
    sort_xlift: float | None = None  # xLift summed over the sort categories (013)
    eligibility: Eligibility


class PlayerPage(BaseModel):
    total: int
    players: list[PlayerRow]


class MoveErrorDetail(BaseModel):
    move_index: int
    code: str
    message: str


# --- Player Analysis: the xLift leaderboard (009 contracts/api.md) -------------------------


class LeaderboardRequest(BaseModel):
    league_id: int
    team_id: int
    window: int = Field(82, ge=1, le=82)
    as_of: date | None = None
    fragility: Fragility = "dab_tag"
    evaluate_for: Literal["team", "league"] = "team"
    # Free agents, everyone, or one fantasy team's players (a team id).
    pool: Literal["free_agents", "all"] | int = "free_agents"
    top: int = Field(25, ge=10, le=50, multiple_of=5)
    min_games: int = Field(5, ge=1, le=15)


class LeaderboardSettings(BaseModel):
    mode: Literal["strategic"]
    window: int
    as_of: date
    fragility: Fragility


class LeaderboardCategory(BaseModel):
    key: str
    label: str
    higher_is_better: bool


class LeaderboardEntry(BaseModel):
    player_id: int
    name: str
    nba_team: str | None
    owner_team_id: int | None  # None = free agent
    owner_label: str
    status: str
    games_found: int
    games_requested: int
    footnote: str | None
    # Net expected weekly category wins added: the sum of `by_category`.
    xlift: float
    # Per category, in the response's `categories` order.
    by_category: list[float]


class Leaderboard(BaseModel):
    settings: LeaderboardSettings
    evaluate_for: Literal["team", "league"]
    team_id: int
    team_name: str
    categories: list[LeaderboardCategory]
    total: int  # eligible players before `top`
    entries: list[LeaderboardEntry]
    warnings: list[WarningModel]


# --- Trade Finder (014) -----------------------------------------------------------------------


class TradesRequest(BaseModel):
    league_id: int
    team_id: int
    window: int = Field(82, ge=1, le=82)
    as_of: date | None = None
    fragility: Fragility = "dab_tag"


class TradePlayer(BaseModel):
    player_id: int
    name: str
    nba_team: str | None
    status: str


class CategoryGain(BaseModel):
    category: str
    gain: float


class Trade(BaseModel):
    """A 1-for-1 swap; both gains are expected weekly category wins, both above zero."""

    give: TradePlayer
    get: TradePlayer
    your_gain: float
    their_gain: float
    your_categories: list[CategoryGain]  # every category, in the format's order


class TradeRow(BaseModel):
    team_id: int
    team_name: str
    manager: str
    trade: Trade | None  # None: no 1-for-1 swap helps both teams


class TradesResult(BaseModel):
    settings: LeaderboardSettings
    team_id: int
    team_name: str
    categories: list[LeaderboardCategory]
    rows: list[TradeRow]
    warnings: list[WarningModel]
