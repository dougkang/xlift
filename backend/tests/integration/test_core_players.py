from ffmodel.core.data import get_player, search_players
from tests.fixtures import dataset as fx


def ids(players):
    return [p.player_id for p in players]


def test_accent_and_partial_search(fixture_engine):
    with fixture_engine.connect() as conn:
        for q in ("doncic", "Dončić", "lu don"):
            assert ids(search_players(conn, q))[0] == fx.DONCIC, q
        assert set(ids(search_players(conn, "marcus twin"))) == {fx.TWIN_LAL, fx.TWIN_GSW}
        assert ids(search_players(conn, "schroder")) == [fx.SCHRODER]


def test_active_only_and_limit(fixture_engine):
    with fixture_engine.connect() as conn:
        assert search_players(conn, "vet", active_only=True) == []
        assert ids(search_players(conn, "vet")) == [fx.OLD_VET]
        assert len(search_players(conn, "a", limit=2)) == 2


def test_get_player(fixture_engine):
    with fixture_engine.connect() as conn:
        luka = get_player(conn, fx.DONCIC)
        vet = get_player(conn, fx.OLD_VET)
        assert get_player(conn, 9999) is None
    assert luka.positions == ("G", "F") and luka.current_team == "LAL"
    assert vet.current_team is None and not vet.is_active
