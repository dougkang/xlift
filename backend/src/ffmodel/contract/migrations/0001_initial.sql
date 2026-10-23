-- FF-Model data contract, schema version 1.
-- This is the contract between data sources and the engine/tools (Constitution VI).
-- Portable SQL: no vendor-specific types or features. Booleans are INTEGER 0/1 and dates are ISO-8601
-- TEXT (YYYY-MM-DD). Moving to another engine needs only mechanical DDL changes, e.g. auto-numbered
-- `INTEGER PRIMARY KEY` becomes an IDENTITY column on PostgreSQL.
-- Migration 0001 applies exactly this DDL.

CREATE TABLE season (
    season_id   TEXT PRIMARY KEY CHECK (length(season_id) = 7),
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    CHECK (end_date >= start_date)
);

CREATE TABLE nba_team (
    team_id      INTEGER PRIMARY KEY,
    abbreviation TEXT NOT NULL UNIQUE,
    city         TEXT NOT NULL,
    name         TEXT NOT NULL
);

CREATE TABLE nba_team_external_id (
    source      TEXT NOT NULL,
    external_id TEXT NOT NULL,
    team_id     INTEGER NOT NULL REFERENCES nba_team (team_id),
    PRIMARY KEY (source, external_id)
);

CREATE TABLE player (
    player_id       INTEGER PRIMARY KEY,
    full_name       TEXT NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    search_name     TEXT NOT NULL,
    positions       TEXT,
    current_team_id INTEGER REFERENCES nba_team (team_id),
    is_active       INTEGER NOT NULL CHECK (is_active IN (0, 1))
);
CREATE INDEX ix_player_search_name ON player (search_name);

CREATE TABLE player_external_id (
    source       TEXT NOT NULL,
    external_id  TEXT NOT NULL,
    player_id    INTEGER NOT NULL REFERENCES player (player_id),
    match_method TEXT NOT NULL CHECK (match_method IN ('exact', 'auto', 'user')),
    PRIMARY KEY (source, external_id)
);
CREATE INDEX ix_player_external_id_player ON player_external_id (player_id);

CREATE TABLE game (
    game_id      INTEGER PRIMARY KEY,
    season_id    TEXT NOT NULL REFERENCES season (season_id),
    season_type  TEXT NOT NULL CHECK (season_type IN
                 ('preseason', 'regular', 'all_star', 'playoffs', 'play_in', 'cup_final')),
    game_date    TEXT NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES nba_team (team_id),
    away_team_id INTEGER NOT NULL REFERENCES nba_team (team_id),
    status       TEXT NOT NULL CHECK (status IN ('scheduled', 'final', 'postponed', 'cancelled')),
    CHECK (home_team_id <> away_team_id)
);
CREATE INDEX ix_game_season_type_date ON game (season_id, season_type, game_date);
CREATE INDEX ix_game_home_date ON game (home_team_id, game_date);
CREATE INDEX ix_game_away_date ON game (away_team_id, game_date);

CREATE TABLE game_external_id (
    source      TEXT NOT NULL,
    external_id TEXT NOT NULL,
    game_id     INTEGER NOT NULL REFERENCES game (game_id),
    PRIMARY KEY (source, external_id)
);

CREATE TABLE player_game (
    game_id    INTEGER NOT NULL REFERENCES game (game_id),
    player_id  INTEGER NOT NULL REFERENCES player (player_id),
    team_id    INTEGER NOT NULL REFERENCES nba_team (team_id),
    minutes    REAL    NOT NULL CHECK (minutes >= 0),
    fgm        INTEGER NOT NULL CHECK (fgm >= 0),
    fga        INTEGER NOT NULL CHECK (fga >= fgm),
    fg3m       INTEGER NOT NULL CHECK (fg3m >= 0 AND fg3m <= fgm),
    fg3a       INTEGER NOT NULL CHECK (fg3a >= fg3m AND fg3a <= fga),
    ftm        INTEGER NOT NULL CHECK (ftm >= 0),
    fta        INTEGER NOT NULL CHECK (fta >= ftm),
    oreb       INTEGER NOT NULL CHECK (oreb >= 0),
    dreb       INTEGER NOT NULL CHECK (dreb >= 0),
    reb        INTEGER NOT NULL CHECK (reb = oreb + dreb),
    ast        INTEGER NOT NULL CHECK (ast >= 0),
    stl        INTEGER NOT NULL CHECK (stl >= 0),
    blk        INTEGER NOT NULL CHECK (blk >= 0),
    tov        INTEGER NOT NULL CHECK (tov >= 0),
    pf         INTEGER NOT NULL CHECK (pf >= 0),
    pts        INTEGER NOT NULL CHECK (pts >= 0),
    plus_minus INTEGER,
    PRIMARY KEY (game_id, player_id)
);
CREATE INDEX ix_player_game_player ON player_game (player_id, game_id);

CREATE TABLE player_team_stint (
    player_id  INTEGER NOT NULL REFERENCES player (player_id),
    team_id    INTEGER NOT NULL REFERENCES nba_team (team_id),
    start_date TEXT    NOT NULL,
    end_date   TEXT,
    PRIMARY KEY (player_id, start_date),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE fantasy_league (
    league_id              INTEGER PRIMARY KEY,
    league_key             TEXT    NOT NULL UNIQUE,
    name                   TEXT    NOT NULL,
    season_id              TEXT    NOT NULL REFERENCES season (season_id),
    scoring_format_id      TEXT    NOT NULL,
    active_roster_capacity INTEGER NOT NULL CHECK (active_roster_capacity > 0)
);

CREATE TABLE manager (
    manager_id   INTEGER PRIMARY KEY,
    league_id    INTEGER NOT NULL REFERENCES fantasy_league (league_id),
    display_name TEXT    NOT NULL,
    UNIQUE (league_id, display_name)
);

CREATE TABLE fantasy_team (
    fantasy_team_id INTEGER PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES fantasy_league (league_id),
    source_team_key TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    manager_id      INTEGER NOT NULL REFERENCES manager (manager_id),
    UNIQUE (league_id, source_team_key)
);

CREATE TABLE roster_entry (
    league_id        INTEGER NOT NULL REFERENCES fantasy_league (league_id),
    player_id        INTEGER NOT NULL REFERENCES player (player_id),
    fantasy_team_id  INTEGER NOT NULL REFERENCES fantasy_team (fantasy_team_id),
    slot             TEXT    NOT NULL CHECK (slot IN ('active', 'reserve')),
    source_positions TEXT,
    PRIMARY KEY (league_id, player_id)
);
CREATE INDEX ix_roster_entry_team ON roster_entry (fantasy_team_id);

CREATE TABLE player_status (
    player_id INTEGER NOT NULL REFERENCES player (player_id),
    source    TEXT    NOT NULL,
    as_of     TEXT    NOT NULL,
    status    TEXT    NOT NULL CHECK (status IN
              ('healthy', 'DTD', 'GTD', 'Q', 'O', 'SUSP', 'IL', 'IL+', 'NA')),
    PRIMARY KEY (player_id, source, as_of)
);

CREATE TABLE load_run (
    run_id        INTEGER PRIMARY KEY,
    source        TEXT    NOT NULL,
    scope         TEXT    NOT NULL,
    started_at    TEXT    NOT NULL,
    finished_at   TEXT,
    outcome       TEXT    NOT NULL CHECK (outcome IN ('running', 'succeeded', 'failed', 'rejected')),
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    rows_updated  INTEGER NOT NULL DEFAULT 0,
    report        TEXT
);
