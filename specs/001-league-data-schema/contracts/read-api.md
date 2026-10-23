# Contract: Core Data Read Interface (`ffmodel.core.data`)

This is the only way the engine and tools read league and player data (FR-020 to FR-024). Every
function takes a SQLAlchemy `Connection` and runs plain SQL against [schema.sql](schema.sql).
Nothing here imports an adapter (Constitution VI).

Return types are frozen dataclasses. Dates are `datetime.date`. Every function counts
regular-season games only (`game.season_type = 'regular'`, FR-012). There is no parameter to
include postseason, preseason, or other types.

## Players

```python
def search_players(conn, query: str, *, active_only: bool = False, limit: int = 25) -> list[PlayerSummary]
def get_player(conn, player_id: int) -> PlayerSummary | None

@dataclass(frozen=True)
class PlayerSummary:
    player_id: int
    full_name: str
    positions: tuple[str, ...]        # ("G", "F")
    current_team: str | None          # NBA team abbreviation
    is_active: bool
```

- `search_players` ignores case and accents and matches partial names (FR-023). The query is
  normalized and split into words, and every word must appear in `search_name`
  (`LIKE '%w1%' AND LIKE '%w2%' …`). `"doncic"`, `"Dončić"` and `"lu don"` all find Luka Dončić. Results are ordered by exact-prefix match first, then
  by name.

## Game history

```python
def get_last_n_games(conn, player_id: int, n: int, *, as_of: date | None = None) -> GameWindow
def get_player_history(conn, player_id: int, *, seasons: Sequence[str] | None = None
                       ) -> list[PlayerGameLine]

@dataclass(frozen=True)
class GameWindow:
    player_id: int
    requested: int                    # n
    found: int                        # len(games); < requested ⇒ tools flag with an asterisk
    games: tuple[PlayerGameLine, ...] # newest first, may span seasons

    @property
    def is_short(self) -> bool: ...   # found < requested

@dataclass(frozen=True)
class PlayerGameLine:
    game_id: int
    season_id: str
    game_date: date
    team: str                         # team abbreviation played for
    opponent: str
    minutes: float
    fgm: int; fga: int; fg3m: int; fg3a: int; ftm: int; fta: int
    oreb: int; dreb: int; reb: int; ast: int; stl: int; blk: int; tov: int; pf: int; pts: int
    plus_minus: int | None
```

- `get_last_n_games` crosses season boundaries until it has `n` games or runs out (FR-020,
  FR-020a). `as_of` excludes games after that date; the default is today.
- Raw components only. Percentages and category values are computed by scoring formats, never
  here.

## Schedule and availability

```python
def count_team_games(conn, player_id: int, start: date, end: date, *,
                     statuses: Sequence[str] = ("final", "scheduled")) -> int
def get_availability(conn, player_id: int, start: date, end: date) -> Availability

@dataclass(frozen=True)
class Availability:
    player_id: int
    team_games: int     # final games of the team the player was on (by stint)
    games_played: int   # appearances
    @property
    def games_missed(self) -> int: ...  # team_games - games_played
```

- Tactical mode calls `count_team_games(p, today, week_end, statuses=("scheduled",))`. Historical
  checks use `statuses=("final",)`.
- A postponed or cancelled game is never counted.

## League

```python
def list_leagues(conn) -> list[LeagueSettings]
def get_league(conn, league_id: int) -> LeagueSnapshot
def get_free_agents(conn, league_id: int) -> list[PlayerSummary]

@dataclass(frozen=True)
class LeagueSettings:
    league_id: int
    league_key: str
    name: str
    season_id: str
    scoring_format_id: str            # resolved by the scoring-format registry in a later feature
    active_roster_capacity: int

@dataclass(frozen=True)
class LeagueSnapshot:
    settings: LeagueSettings
    teams: tuple[FantasyTeamView, ...]

@dataclass(frozen=True)
class FantasyTeamView:
    fantasy_team_id: int
    source_team_key: str
    name: str
    manager: str
    roster: tuple[RosterPlayer, ...]

@dataclass(frozen=True)
class RosterPlayer:
    player: PlayerSummary
    slot: str                         # "active" | "reserve"
    status: str                       # latest player_status, "healthy" if none
```

- `get_league` orders teams by `source_team_key`, and each roster by slot (`active` first), then
  `full_name`.
- `get_league` returns the original state as loaded (FR-019). Tools apply hypothetical moves to
  this immutable snapshot in memory.
- `get_free_agents` returns active NBA players not on any roster in the league.

## Contract tests

- Every function is exercised against the fixture dataset (FR-025, SC-006) with networking disabled.
- Each acceptance scenario in the spec's US3 and US4, including "4 + 11 across seasons" and
  "3 of 15 found", is a named test.
