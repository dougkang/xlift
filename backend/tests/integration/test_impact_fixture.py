from ffmodel.core.data import count_team_games_bulk, get_league
from ffmodel.core.scenario import from_snapshot
from tests.fixtures import impact_dataset as fx
from tests.invariants import assert_contract_invariants


def test_fixture(impact_engine):
    with impact_engine.connect() as conn:
        assert_contract_invariants(conn)
        one_per_team = {fx.BUSY: fx.BOS, fx.STEADY: fx.MIA, fx.BENCH: fx.NYK, fx.GAMMA_1: fx.CHI}
        counts = count_team_games_bulk(
            conn, list(one_per_team), fx.IMPACT_TODAY, fx.WEEK[1], statuses=("scheduled",)
        )
        assert {one_per_team[p]: n for p, n in counts.items()} == fx.GAMES_REMAINING
        scenario = from_snapshot(get_league(conn, 1))
    scenario.check_invariants()
    assert scenario.open_active_slots(3) == 1
    assert scenario.open_active_slots(1) == 0
