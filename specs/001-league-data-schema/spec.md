# Feature Specification: League Data Schema & NBA Stats Ingestion

**Feature Branch**: `001-league-data-schema`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "define a schema that would support @docs/tool1-impact-analysis.md and an eventual player comparison tool. provide an initial implementation that uses https://github.com/swar/nba_api to fill the db."

## Overview

Every tool in this project reads league and player data through one shared data contract (a
database schema). The source of the data is never visible to the tools. This feature defines that contract so it can hold
everything the Impact Analysis tool (`docs/tool1-impact-analysis.md`) and a future Player
Comparison tool need. It also delivers the first two data sources.

The contract has two halves:

- **NBA reality**: real players, NBA teams, games, per-game box scores, schedules. Filled by the
  NBA stats loader from the public NBA stats source (`nba_api`).
- **Fantasy league**: league settings, fantasy teams, managers, rosters, and current player status.
  Filled by a roster file loader that reads a roster export in the format of
  `~/dev/ccsv-rumble-page/data/rosters.csv`.

Fantasy matchups are not stored. In tactical mode the user picks the opponent and the matchup
dates. Strategic mode compares against every team, so it needs no schedule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load NBA player game history (Priority: P1)

As the person running the project, I run one load command and get every NBA player's per-game box
score for the configured seasons in the local database. Each player's recent game history is then
available to fit stat distributions.

**Why this priority**: Every tool depends on per-game player stats. Without them there is nothing to
fit, simulate, or compare.

**Independent Test**: Run the loader for one season against an empty database. Then confirm that a
chosen player's game log in the database matches the official game log for that season, game for
game.

**Acceptance Scenarios**:

1. **Given** an empty database, **When** the loader runs for a regular season, **Then** every player
   who appeared in a game that season exists with one row per game played, holding the raw box
   score components (minutes, made/attempted field goals, threes, free throws, rebounds, assists,
   steals, blocks, turnovers, points, fouls).
2. **Given** a fully loaded season, **When** the loader runs again with no new games, **Then** no
   duplicate rows are created and no existing rows change.
3. **Given** a partially loaded season (new games played since the last load), **When** the
   loader runs, **Then** only the new games are added, and the run takes much less time than a full
   load.
4. **Given** a player traded mid-season, **When** their game log is read, **Then** each game shows
   the NBA team the player played for in that game.

---

### User Story 2 - Load my fantasy league from a roster file (Priority: P1)

As a league member, I load my league's roster file (team ID, player ID, name, positions, NBA team,
status, team name, manager). The league's teams, managers, and rosters then appear in the database,
linked to real NBA players, so Impact Analysis can show and simulate each team.

**Why this priority**: Impact Analysis compares fantasy teams. Without teams and rosters, the tool
has nothing to compare.

**Independent Test**: Load `~/dev/ccsv-rumble-page/data/rosters.csv` (18 teams, 184 roster rows).
Confirm that all 18 teams and managers appear, every roster row links to exactly one NBA player,
and every other NBA player shows as a free agent.

**Acceptance Scenarios**:

1. **Given** loaded NBA players, **When** the roster file is loaded, **Then** each fantasy team
   appears with its file-provided ID, name, manager, and players.
2. **Given** a roster file whose player names differ from NBA names (abbreviations such as
   "N. Alexander-Walker", suffixes such as "Jimmy Butler III", accents such as "Nikola Jokić"),
   **When** it is loaded, **Then** each row is matched to the correct NBA player. Rows that cannot
   be matched with confidence are listed for the user to resolve, and nothing is linked silently
   to the wrong player.
3. **Given** a user-provided match for an unresolved row, **When** the file is loaded again,
   **Then** that match is used and remembered for future loads.
4. **Given** a loaded league, **When** a tool asks for free agents, **Then** it gets every NBA player
   not on any roster in that league.
5. **Given** a roster row with a status (Q, O, IL, NA, or blank), **When** the file is loaded,
   **Then** that status is stored as the player's current status as of the load.
6. **Given** a newer roster file for the same league, **When** it is loaded, **Then** it replaces
   the league's rosters, and that becomes the "original" state that tools reset to.

---

### User Story 3 - Know who plays when, and how often players miss games (Priority: P2)

As a user of Impact Analysis, I need to know how many games each player's NBA team plays in the
date range of the matchup I pick (tactical mode). I also need to know how often each player has
missed games their team played (strategic mode, injury-proneness).

**Why this priority**: Tactical mode depends on games remaining. Strategic mode depends on how
available each player is. Without this data the two modes give the same answer.

**Independent Test**: For a chosen date range, confirm that the number of games scheduled for each
NBA team matches the official schedule. For a chosen player, confirm that games missed equals the
games their team played minus the games the player appeared in.

**Acceptance Scenarios**:

1. **Given** a loaded NBA schedule and a date range, **When** games per player are requested for
   that range, **Then** each player's count equals the scheduled games of their current NBA team in
   that range.
2. **Given** a player's history, **When** availability is requested over a window, **Then** the
   result separates games played from games their team played, so a missed game is distinct from
   a game with zero production.

---

### User Story 4 - Compare any players across seasons (Priority: P3)

As a user of the future Player Comparison tool, I can retrieve the game history of any NBA player
across multiple seasons, rostered or not. I can also find players by name, including names with
accents or punctuation.

**Why this priority**: The comparison tool is not built yet. The schema must not block it, but it
delivers no value until that tool exists.

**Independent Test**: Retrieve two players' game histories across two seasons, and search for
"Doncic" to find "Luka Dončić".

**Acceptance Scenarios**:

1. **Given** multiple loaded seasons, **When** a player's history is requested, **Then** games from
   all loaded seasons are returned, each tagged with its season and date.
2. **Given** a search for a name without accents, **When** a player whose name has accents
   exists, **Then** that player is found.
3. **Given** a player who has retired or not played this season, **When** their history is
   requested, **Then** past seasons are still returned.
4. **Given** a player with 4 games this season and 70 last season, **When** their last 15 games
   are requested, **Then** the 4 current-season games and the 11 most recent previous-season games
   are returned.
5. **Given** a rookie with 3 games in total, **When** their last 15 games are requested, **Then**
   all 3 games are returned, along with "3 of 15 found".

---

### Edge Cases

- A player has zero attempts in a game (e.g. 0 FTA): only the made and attempted counts are
  stored, never a percentage, so nothing divides by zero.
- A player was active but did not play (DNP), or was not with the team: this is recorded as not
  having played, never as a game with all-zero stats.
- Early in a season, few current-season games exist. "Last N games" MUST cross into the previous
  season, in date order.
- A rookie has few or no NBA games (e.g. a player drafted this year). Their history returns
  whatever exists, possibly nothing, together with the found-versus-requested count (FR-020a).
  How to model a thin history belongs to the tools.
- A game is postponed or rescheduled: the schedule reflects the new date after the next load, with
  no duplicate games.
- The NBA stats source rate-limits, times out, or returns an error mid-load: the load stops or
  retries without leaving a half-written game. Rerunning finishes the job (see FR-006).
- The roster file's NBA team for a player differs from the NBA data, for example after a recent
  trade. The NBA data decides the player's current team. The file's team is used only to help
  match names.
- Two players share a name: players are identified by a stable ID. Name matching uses the NBA team
  to tell them apart, and otherwise sends the row to the user to resolve.
- The same player appears on two teams in one roster file: the load is rejected, and both rows are
  reported.
- Roster sizes in the file differ by team (10–12 in the reference file, because reserve-status
  players add to the count). See FR-017.
- A player appears in a game that hasn't finished: only completed games are stored as box scores.

## Requirements *(mandatory)*

### Functional Requirements

**Data contract (schema)**

- **FR-001**: The system MUST define a single, versioned data contract (database schema) that holds
  NBA players, NBA teams, seasons, games, per-player-per-game box scores, the NBA schedule, fantasy
  leagues, fantasy teams, managers, roster entries, and player status snapshots.
- **FR-002**: Box scores MUST store raw, additive components only (minutes, FGM, FGA, 3PM, 3PA,
  FTM, FTA, OREB, DREB, REB, AST, STL, BLK, TOV, PF, PTS, plus/minus). Percentages and fantasy
  category values MUST NOT be stored. Scoring formats derive them (Constitution I & II).
- **FR-003**: The contract MUST NOT contain any scoring-format-specific structure, such as a
  fixed set of 9 category columns. A league references its scoring format by identifier only.
- **FR-004**: The contract MUST NOT contain anything specific to a data source. Any other data
  source (another stats provider, a fantasy platform, test fixtures) MUST be able to fill it with
  no schema change. Source-specific identifiers (e.g. NBA stats player IDs, roster-file player IDs
  such as `nba.p.5473`) MUST be stored as source-labeled external IDs on the player.
- **FR-005**: Schema changes MUST be applied through ordered, versioned migrations. The current
  schema version MUST be readable from the database.

**NBA stats loader**

- **FR-006**: The system MUST provide a loader that fills the NBA side of the contract from the NBA
  stats source (`nba_api`) for one or more seasons given by the user.
- **FR-007**: Loads MUST be idempotent and incremental. A rerun adds only new or changed games and
  never creates duplicates.
- **FR-008**: A failed or interrupted load MUST NOT leave partially written games. A game's data
  is either fully present or absent.
- **FR-009**: The loader MUST pace its requests and retry transient failures so that a full-season
  load works within the source's rate limits.
- **FR-010**: Every loader (NBA stats and roster file) MUST record each run's time, source,
  scope, rows added or updated, and outcome, so the user can tell how fresh the data is.
- **FR-011**: The loader MUST load the NBA schedule, including future games, so that games
  remaining in any date range can be counted.
- **FR-012**: Only regular-season games count in any calculation. This covers last-N windows,
  game counts, missed games, and season totals. Postseason games (play-in and playoffs) MUST NOT
  be considered, and neither are preseason, All-Star, or NBA Cup final games, which are not
  regular season. The NBA stats loader MUST load regular-season games only. Every game MUST still
  be labeled with its season type, so reads can filter on it if another source stores other
  types.
- **FR-013**: The engine and tools MUST NOT import or depend on any loader (Constitution VI).

**Roster file loader**

- **FR-014**: The system MUST provide a loader that reads a roster file with the columns `team_id`,
  `player_id`, `name`, `positions`, `nba_team`, `status`, `team_name`, `manager`. It creates or
  updates one fantasy league with its teams, managers, and roster entries.
- **FR-015**: League settings the file does not contain (league name, season, scoring format ID,
  roster capacity) MUST be supplied when the file is loaded. The defaults are the current season
  and the 9cat h2h format.
- **FR-016**: Each roster row MUST be matched to exactly one NBA player as follows. First use a
  match the user has confirmed for that file's player ID. Matches found automatically are
  recomputed on every load, not reused. Otherwise match on the normalized name:
  ignore case, accents, punctuation, and suffixes such as Jr./III, allow abbreviated first names,
  and use the NBA team to break ties. Rows with no confident match MUST be reported. The
  league is not partially loaded while any row is unresolved. A user-confirmed match MUST be
  stored and reused.
- **FR-017**: Roster capacity MUST be a league setting that counts only active roster spots.
  Players whose status is a reserve status (IL, NA) do not count toward it. A load MUST reject a
  team whose active players exceed capacity, and MUST reject a player listed on more than one team.
  Every rejected row MUST be reported. Reserve slots have no capacity setting. Only players who
  are in a reserve slot in the loaded roster can be in one. Tools never place an added or swapped
  player into a reserve slot (see `docs/tool1-impact-analysis.md`).
- **FR-018**: A player's roster-file status (Q, O, IL, NA, blank) MUST be stored as a dated status
  snapshot, so tools can see current availability.
- **FR-019**: Loading a roster file replaces the league's roster entries, and the result is the
  league's "original" state. Hypothetical add/drop/swap moves made in tools MUST NOT be written to
  the contract (Constitution VII). Free agents are the NBA players not on any roster in the league
  and are not stored separately.

**Read support for tools**

- **FR-020**: Tools MUST be able to retrieve, for any player, their last N games played (N chosen
  by the user) in date order, with the raw components. If the current season has fewer than N
  games, the result MUST reach back into earlier loaded seasons until it has N. Each game MUST be
  tagged with its season.
- **FR-020a**: When a player has fewer than N games in all loaded seasons, the result MUST return
  every game that exists and MUST say how many were found against how many were requested. Tools
  use this to flag the player; Impact Analysis shows an asterisk footnote.
- **FR-021**: Tools MUST be able to retrieve, for any player and date range, the number of games
  their NBA team played or is scheduled to play, and the number they appeared in.
- **FR-022**: Tools MUST be able to retrieve a league's settings, teams, managers, rosters, free
  agents, and each rostered player's latest status.
- **FR-023**: Player name search MUST ignore case and accents and match partial names.
- **FR-024**: Each player MUST carry the descriptive attributes a comparison tool needs: name,
  positions, current NBA team, and active status.
- **FR-025**: The contract MUST ship with a small fixture dataset (a few NBA teams, players,
  games, and one fantasy league) that loads through the same contract and is used by automated
  tests.

### Key Entities

- **Season**: an NBA season (e.g. 2026-27) with its start and end dates. Games and leagues belong to
  one season.
- **NBA Team**: a real NBA franchise (name, abbreviation).
- **Player**: a real NBA player with a stable internal ID, name, a search-friendly name, positions,
  current NBA team, and active status.
- **Player External ID**: a source-labeled identifier for a player (e.g. NBA stats ID, roster-file
  `nba.p.*` ID), including user-confirmed matches.
- **Game**: one NBA game (date, season, season type, home and away teams, status: scheduled /
  final / postponed). Future games make up the schedule.
- **Player Game**: one appearance by a player in a completed game: the team they played for and the
  raw box score components. A missing row means the player did not play. Basis of every
  distribution fit.
- **Team Stint**: a date range during which a player belonged to an NBA team (open-ended for the
  current team). Used to count a player's team games, missed games, and upcoming games.
- **Fantasy League**: a league for one season, with its scoring format ID and active roster
  capacity.
- **Manager**: the person who runs a fantasy team.
- **Fantasy Team**: a team in a league, with its source ID, name, and manager.
- **Roster Entry**: a player on a fantasy team, as of the latest roster load.
- **Player Status**: a player's availability status (Q, O, IL, NA, healthy) as of a given date,
  with its source.
- **Load Run**: a record of one data load: source, scope, time, rows changed, outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first load of one full regular season completes unattended in under 30 minutes. A
  daily refresh after that completes in under 5 minutes.
- **SC-002**: For 20 randomly chosen players, each player's season totals for every stored stat
  computed from the database exactly match the official season totals.
- **SC-003**: Running either loader twice in a row with no new input changes zero rows of league
  and player data. The run itself is still logged (FR-010).
- **SC-004**: Games remaining per NBA team for any 7-day window match the official schedule for
  100% of teams.
- **SC-005**: Loading the reference roster file (184 rows) matches at least 95% of rows
  automatically and correctly. After the user resolves the rest once, a reload matches 100% with no
  prompts.
- **SC-006**: The fixture dataset loads through the contract, and all reads in FR-020–FR-024
  return correct results against it with the NBA stats source unreachable. This proves the tools
  don't depend on the source.
- **SC-007**: Every input that Impact Analysis lists in `docs/tool1-impact-analysis.md` can be
  answered from the database alone: last-X-game distributions, games in a chosen date range,
  missed games, rosters, free agents, current status, and all league teams.

## Assumptions

- The reference roster file is a Yahoo-style export from the ccsv-rumble-page project, and it is
  enough for the fantasy side: 18 teams, team IDs, names, managers, players, and status. It does
  not hold league settings (scoring format, roster capacity) or a matchup schedule. Settings
  come from FR-015. Matchups are not needed (below).
- **Matchups are chosen in the tool, not stored.** Tactical mode: the user picks the opponent, and
  the matchup dates default to the current fantasy week (Monday–Sunday). Strategic mode: the
  selected team is compared round-robin against every other team, so no schedule is needed. If a
  future feature needs schedule strength or playoff path, the matchup schedule would be added as a
  new migration.
- Tactical mode counts only games remaining from today through the end of the chosen range.
  Stats already accrued in the current matchup are out of scope for this feature.
- Default active roster capacity is 10, inferred from the reference file: after excluding IL/NA
  players, no team has more than 10. The user can override it.
- The default load scope is the current (2026-27) and previous (2025-26) NBA regular seasons. Users
  can pick other seasons. Early in the current season, this gives "last N games" enough history.
- Injury-proneness comes from games missed (the team played, the player did not). Current status
  (Q/O/IL/NA) comes from the roster file. The NBA stats source has no reliable injury reports.
- Positions are taken from the NBA data for all players. The roster file's positions (G, FC) are
  kept only as source data. Positional roster slots are out of scope.
- Loads are run on demand by the user. Scheduled automatic refresh is out of scope.
- One local user; no authentication or multi-user access in this feature.
- Dependency: the public NBA stats source accessed through the open-source `nba_api` project. It is
  unofficial and may rate-limit or change without notice; that risk is isolated to the loader.
