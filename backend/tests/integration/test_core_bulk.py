from datetime import date

from sqlalchemy import text

from ffmodel.core.data import (
    count_team_games,
    count_team_games_bulk,
    get_data_freshness,
    get_last_n_games,
    get_last_n_games_bulk,
)
from tests.fixtures import dataset as fx

ALL = [p[0] for p in fx.PLAYERS]


def test_last_n_bulk_matches_single(fixture_engine):
    with fixture_engine.connect() as conn:
        bulk = get_last_n_games_bulk(conn, ALL, 15, as_of=fx.FIXTURE_TODAY)
        for pid in ALL:
            assert bulk[pid] == get_last_n_games(conn, pid, 15, as_of=fx.FIXTURE_TODAY), pid
    assert (bulk[fx.DYBANTSA].found, bulk[fx.DONCIC].found) == (3, 15)


def test_team_games_bulk_matches_single(fixture_engine):
    windows = [
        (date(2026, 10, 20), date(2026, 10, 29)),
        (date(2026, 10, 31), date(2026, 11, 8)),
        (fx.S2526_START, fx.S2526_END),
    ]
    with fixture_engine.connect() as conn:
        for statuses in (("final",), ("scheduled",), ("final", "scheduled")):
            for a, b in windows:
                bulk = count_team_games_bulk(conn, ALL, a, b, statuses=statuses)
                for pid in ALL:
                    assert bulk[pid] == count_team_games(conn, pid, a, b, statuses=statuses)


def test_freshness(fixture_engine):
    with fixture_engine.connect() as conn:
        f = get_data_freshness(conn, 1)
        assert f.nba_data_loaded_at is None and f.roster_as_of == "2026-10-29"
        conn.execute(
            text(
                "INSERT INTO load_run (source, scope, started_at, finished_at, outcome)"
                " VALUES ('nba_stats', '{}', 'x', '2026-10-30T01:00:00+00:00', 'succeeded')"
            )
        )
        assert get_data_freshness(conn, 1).nba_data_loaded_at == "2026-10-30T01:00:00+00:00"
