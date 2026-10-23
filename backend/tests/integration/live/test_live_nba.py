"""Real-source checks (SC-001, SC-002, SC-004). Manual: uv run pytest -m live"""

import random
import time
from collections import Counter
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from ffmodel.adapters.nba_stats.loader import load_nba
from ffmodel.adapters.nba_stats.mapping import current_season, previous_season

pytestmark = pytest.mark.live
STATS = [
    "FGM",
    "FGA",
    "FG3M",
    "FG3A",
    "FTM",
    "FTA",
    "OREB",
    "DREB",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "PTS",
]


@pytest.fixture(scope="module")
def loaded(tmp_path_factory):
    from ffmodel.contract.db import get_engine
    from ffmodel.contract.migrate import migrate

    eng = get_engine(f"sqlite:///{tmp_path_factory.mktemp('live')}/live.sqlite")
    migrate(eng)
    season = current_season(date.today())
    started = time.monotonic()
    load_nba(eng, seasons=[season])
    full_seconds = time.monotonic() - started
    return eng, season, full_seconds


def test_sc001_full_load_and_refresh(loaded):
    eng, season, full_seconds = loaded
    assert full_seconds < 30 * 60
    started = time.monotonic()
    summary = load_nba(eng, seasons=[season])
    assert time.monotonic() - started < 5 * 60
    assert (summary.total_inserted, summary.total_updated) == (0, 0)


def test_sc002_season_totals_match_official(tmp_path):
    from nba_api.stats.endpoints import leaguedashplayerstats

    from ffmodel.contract.db import get_engine
    from ffmodel.contract.migrate import migrate

    season = previous_season(current_season(date.today()))  # a complete season
    eng = get_engine(f"sqlite:///{tmp_path}/sc002.sqlite")
    migrate(eng)
    load_nba(eng, seasons=[season])
    official = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        per_mode_detailed="Totals",
        season_type_all_star="Regular Season",
        timeout=60,
    ).get_data_frames()[0]
    official = official[official["GP"] >= 10]
    sample = official.sample(20, random_state=random.randint(0, 10_000))
    cols = ", ".join(f"SUM({s.lower()})" for s in STATS)
    with eng.connect() as conn:
        for _, row in sample.iterrows():
            ours = conn.execute(
                text(
                    f"SELECT {cols} FROM player_game pg"
                    " JOIN player_external_id e ON e.player_id = pg.player_id"
                    " AND e.source = 'nba_stats' WHERE e.external_id = :pid"
                ),
                {"pid": str(row["PLAYER_ID"])},
            ).one()
            official_totals = [int(row[s]) for s in STATS]
            # The NBA's season-totals and game-log endpoints disagree by 1 for a handful of
            # player-stats (stat corrections not propagated). Allow that, never more.
            diffs = [abs(a - b) for a, b in zip(ours, official_totals, strict=True)]
            assert max(diffs) <= 1, (row["PLAYER_NAME"], list(ours), official_totals)


def test_sc002_matches_game_log_exactly(loaded):
    """Load fidelity: our totals equal the sum of the source game log, with no tolerance."""
    from nba_api.stats.endpoints import leaguegamelog

    eng, season, _ = loaded
    log = leaguegamelog.LeagueGameLog(
        season=season,
        player_or_team_abbreviation="P",
        season_type_all_star="Regular Season",
        timeout=60,
    ).get_data_frames()[0]
    expected = {
        str(pid): [int(v) for v in vals]
        for pid, vals in log.groupby("PLAYER_ID")[STATS].sum().iterrows()
    }
    cols = ", ".join(f"SUM({s.lower()})" for s in STATS)
    with eng.connect() as conn:
        ours = {
            pid: list(vals)
            for pid, *vals in conn.execute(
                text(
                    f"SELECT e.external_id, {cols} FROM player_game pg"
                    " JOIN player_external_id e ON e.player_id = pg.player_id"
                    " AND e.source = 'nba_stats' GROUP BY e.external_id"
                )
            )
        }
    assert ours == expected


def test_sc004_next_week_game_counts(loaded):
    from nba_api.stats.endpoints import scheduleleaguev2

    eng, season, _ = loaded
    start = date.today()
    end = start + timedelta(days=6)
    sched = scheduleleaguev2.ScheduleLeagueV2(season=season, timeout=60).get_data_frames()[0]
    expected = Counter()
    for _, g in sched.iterrows():
        day = g["gameDateEst"][:10]
        if (
            g["gameId"].startswith("002")
            and g["postponedStatus"] != "Y"
            and start.isoformat() <= day <= end.isoformat()
        ):
            expected[str(g["homeTeam_teamId"])] += 1
            expected[str(g["awayTeam_teamId"])] += 1
    with eng.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT e.external_id, COUNT(*) FROM game g JOIN nba_team_external_id e"
                " ON e.team_id IN (g.home_team_id, g.away_team_id) AND e.source = 'nba_stats'"
                " WHERE g.season_type = 'regular' AND g.status IN ('scheduled', 'final')"
                " AND g.game_date BETWEEN :a AND :b GROUP BY e.external_id"
            ),
            {"a": start.isoformat(), "b": end.isoformat()},
        ).all()
    assert dict(rows) == dict(expected)
