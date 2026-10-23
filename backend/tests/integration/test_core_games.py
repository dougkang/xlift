from dataclasses import fields
from datetime import date

from sqlalchemy import text

from ffmodel.core.data import get_last_n_games, get_player_history
from ffmodel.core.data.models import PlayerGameLine
from tests.fixtures import dataset as fx


def test_window_spans_seasons(fixture_engine):
    with fixture_engine.connect() as conn:
        w = get_last_n_games(conn, fx.DONCIC, 15, as_of=fx.FIXTURE_TODAY)
    assert (w.found, w.requested, w.is_short) == (15, 15, False)
    assert [g.season_id for g in w.games] == ["2026-27"] * 4 + ["2025-26"] * 11
    assert [g.game_id for g in w.games[4:]] == [fx.lal_game_id(k) for k in range(71, 60, -1)]
    assert all(g.game_id not in (3001, 3002, 3003) for g in w.games)
    assert [g.game_date for g in w.games] == sorted((g.game_date for g in w.games), reverse=True)


def test_short_history(fixture_engine):
    with fixture_engine.connect() as conn:
        w = get_last_n_games(conn, fx.DYBANTSA, 15, as_of=fx.FIXTURE_TODAY)
    assert (w.found, w.requested, w.is_short) == (3, 15, True)


def test_as_of(fixture_engine):
    with fixture_engine.connect() as conn:
        w = get_last_n_games(conn, fx.DONCIC, 15, as_of=date(2026, 10, 19))
    assert w.found == 15 and {g.season_id for g in w.games} == {"2025-26"}


def test_history(fixture_engine):
    with fixture_engine.connect() as conn:
        vet = get_player_history(conn, fx.OLD_VET)
        this_season = get_player_history(conn, fx.DONCIC, seasons=["2026-27"])
        everything = get_player_history(conn, fx.DONCIC)
    assert len(vet) == 30 and {g.season_id for g in vet} == {"2025-26"}
    assert len(this_season) == 4
    assert len(everything) == 74


def test_line_matches_stored_row(fixture_engine):
    with fixture_engine.connect() as conn:
        line = get_last_n_games(conn, fx.DONCIC, 1, as_of=fx.FIXTURE_TODAY).games[0]
        stored = (
            conn.execute(
                text("SELECT * FROM player_game WHERE game_id = :g AND player_id = :p"),
                {"g": line.game_id, "p": fx.DONCIC},
            )
            .mappings()
            .one()
        )
    assert (line.team, line.opponent) == ("LAL", "ATL")  # G9: LAL vs ATL on 10-28
    for f in fields(PlayerGameLine):
        if f.name in stored:
            assert getattr(line, f.name) == stored[f.name], f.name
    assert not any("pct" in f.name for f in fields(PlayerGameLine))
