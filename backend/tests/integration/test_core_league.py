from ffmodel.core.data import get_free_agents, get_league, list_leagues
from tests.fixtures import dataset as fx


def test_list_leagues(fixture_engine):
    with fixture_engine.connect() as conn:
        (league,) = list_leagues(conn)
    assert league.league_key == "fixture-league"
    assert (league.active_roster_capacity, league.scoring_format_id) == (3, "9cat_h2h")


def test_get_league(fixture_engine):
    with fixture_engine.connect() as conn:
        snap = get_league(conn, 1)
    assert [t.source_team_key for t in snap.teams] == ["t.01", "t.02"]
    alpha = snap.teams[0]
    assert alpha.manager == "Ann"
    assert [(r.player.full_name, r.slot, r.status) for r in alpha.roster] == [
        ("AJ Dybantsa", "active", "healthy"),
        ("Jimmy Butler III", "active", "Q"),
        ("Luka Dončić", "active", "healthy"),
        ("Iggy Injured", "reserve", "IL"),
    ]
    assert alpha.roster[2].player.positions == ("G", "F")


def test_free_agents(fixture_engine):
    with fixture_engine.connect() as conn:
        agents = {p.player_id for p in get_free_agents(conn, 1)}
    rostered = {fx.DONCIC, fx.BUTLER, fx.DYBANTSA, fx.IGGY, fx.NAW, fx.SCHRODER}
    assert not agents & rostered
    assert fx.FRED in agents and fx.OLD_VET not in agents
