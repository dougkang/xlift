from datetime import date

from ffmodel.core.data import count_team_games, get_availability
from tests.fixtures import dataset as fx


def test_upcoming_games_skip_postponed_and_cancelled(fixture_engine):
    with fixture_engine.connect() as conn:
        n = count_team_games(
            conn, fx.IGGY, date(2026, 10, 31), date(2026, 11, 8), statuses=("scheduled",)
        )
    assert n == 3  # S2, S4, S7


def test_missed_games(fixture_engine):
    with fixture_engine.connect() as conn:
        a = get_availability(conn, fx.IGGY, date(2026, 10, 20), date(2026, 10, 29))
    assert (a.team_games, a.games_played, a.games_missed) == (4, 2, 2)


def test_traded_player_counts_each_team(fixture_engine):
    with fixture_engine.connect() as conn:
        a = get_availability(conn, fx.TRADESON, fx.S2526_START, fx.S2526_END)
    assert (a.team_games, a.games_played, a.games_missed) == (18, 17, 1)


def test_rookie(fixture_engine):
    with fixture_engine.connect() as conn:
        a = get_availability(conn, fx.DYBANTSA, date(2026, 10, 20), date(2026, 10, 29))
    assert (a.team_games, a.games_played, a.games_missed) == (4, 3, 1)


def test_regular_season_only(fixture_engine):
    with fixture_engine.connect() as conn:
        # Window covering the play-in (04-15), playoffs (04-19) and preseason (10-10) games.
        post = get_availability(conn, fx.DONCIC, date(2026, 4, 13), date(2026, 10, 19))
        pre = count_team_games(conn, fx.DONCIC, date(2026, 10, 1), date(2026, 10, 19))
    assert (post.team_games, post.games_played, pre) == (0, 0, 0)


def test_retired_player_has_no_team_games(fixture_engine):
    with fixture_engine.connect() as conn:
        n = count_team_games(conn, fx.OLD_VET, fx.S2627_START, fx.S2627_END)
    assert n == 0
