-- Current matchup state per league (005): week-to-date team totals and pairings, imported from
-- the exporter's matchups.csv. One state per league; a re-import replaces it.

CREATE TABLE matchup_state (
    league_id    INTEGER PRIMARY KEY REFERENCES fantasy_league (league_id),
    week         INTEGER NOT NULL CHECK (week >= 0),
    period_start TEXT    NOT NULL,
    period_end   TEXT    NOT NULL CHECK (period_end >= period_start),
    as_of        TEXT    NOT NULL,
    run_id       INTEGER NOT NULL REFERENCES load_run (run_id)
);

CREATE TABLE matchup_team (
    league_id        INTEGER NOT NULL REFERENCES matchup_state (league_id),
    fantasy_team_id  INTEGER NOT NULL REFERENCES fantasy_team (fantasy_team_id),
    opponent_team_id INTEGER NOT NULL REFERENCES fantasy_team (fantasy_team_id),
    fgm  INTEGER NOT NULL CHECK (fgm >= 0),
    fga  INTEGER NOT NULL CHECK (fga >= fgm),
    fg3m INTEGER NOT NULL CHECK (fg3m >= 0 AND fg3m <= fgm),
    ftm  INTEGER NOT NULL CHECK (ftm >= 0),
    fta  INTEGER NOT NULL CHECK (fta >= ftm),
    reb  INTEGER NOT NULL CHECK (reb >= 0),
    ast  INTEGER NOT NULL CHECK (ast >= 0),
    stl  INTEGER NOT NULL CHECK (stl >= 0),
    blk  INTEGER NOT NULL CHECK (blk >= 0),
    tov  INTEGER NOT NULL CHECK (tov >= 0),
    pts  INTEGER NOT NULL CHECK (pts = 2 * fgm + fg3m + ftm),
    PRIMARY KEY (league_id, fantasy_team_id),
    CHECK (opponent_team_id <> fantasy_team_id)
);
