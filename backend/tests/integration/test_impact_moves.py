import json

import pytest
from sqlalchemy import text

from ffmodel.core.scenario import Add, Drop, MoveError, Swap
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.picker import list_players
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

ALPHAS, BETAS, GAMMAS, DELTAS = 1, 2, 3, 4


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def settings(team=GAMMAS):
    return AnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, iterations=2000)


def run(engine, moves=(), team=GAMMAS):
    with engine.connect() as conn:
        return analyze(conn, settings(team), moves)


def roster(result, team):
    return next(r for r in result["rosters"] if r["team_id"] == team)


def ids(result, team):
    return {p["player_id"] for p in roster(result, team)["players"]}


def test_drop_changes_projection_and_frees_player(impact_engine):
    base = run(impact_engine)
    after = run(impact_engine, [Drop(fx.GAMMA_1)])
    assert fx.GAMMA_1 not in ids(after, GAMMAS)
    assert after["category_table"] != base["category_table"]
    with impact_engine.connect() as conn:
        page = list_players(conn, settings(), [Drop(fx.GAMMA_1)], query="gamma one")
    assert page["players"][0]["owner_label"] == "FA"


def test_add_fills_open_slot_and_marks_moved(impact_engine):
    r = run(impact_engine, [Add(fx.BUSY)])
    gammas = roster(r, GAMMAS)
    assert gammas["open_active_slots"] == 0
    busy = next(p for p in gammas["players"] if p["player_id"] == fx.BUSY)
    assert busy["moved"] and busy["slot"] == "active" and busy["name"] == "Busy Streamer"


def test_trade_updates_both_rosters(impact_engine):
    r = run(impact_engine, [Swap(acquire_id=fx.ALPHA_1, give_id=fx.GAMMA_2)])
    assert fx.ALPHA_1 in ids(r, GAMMAS) and fx.GAMMA_2 in ids(r, ALPHAS)


def test_common_random_numbers_for_untouched_teams(impact_engine):
    before = run(impact_engine, team=BETAS)
    # Betas' own samples are unaffected by a Gammas move, so their averages are identical.
    after = run(impact_engine, [Drop(fx.GAMMA_1)], team=GAMMAS)
    betas_after = run(impact_engine, team=BETAS)
    assert (
        before["category_table"]["rows"][0]["average"]
        == betas_after["category_table"]["rows"][0]["average"]
    )
    betas_radar_avg = [r["average"] for r in before["category_table"]["rows"]]
    assert betas_radar_avg == [r["average"] for r in betas_after["category_table"]["rows"]]
    assert after["header"]["team_name"] == "Gammas"


def test_invalid_move_index(impact_engine):
    with pytest.raises(MoveError) as exc:
        run(impact_engine, [Add(fx.BUSY), Add(fx.STEADY)])
    assert (exc.value.move_index, exc.value.code) == (1, "NO_ACTIVE_SLOT")


def checksum(engine):
    tables = [
        "fantasy_league",
        "fantasy_team",
        "manager",
        "roster_entry",
        "player",
        "player_status",
        "player_game",
        "game",
        "player_team_stint",
    ]
    with engine.connect() as conn:
        return json.dumps(
            {
                t: [list(r) for r in conn.execute(text(f"SELECT * FROM {t} ORDER BY 1"))]
                for t in tables
            },
            default=str,
        )


def test_database_never_changes(impact_engine):  # SC-009
    before = checksum(impact_engine)
    moves = [Drop(fx.GAMMA_1), Add(fx.BUSY), Swap(acquire_id=fx.ALPHA_1, give_id=fx.GAMMA_2)]
    for i in range(20):
        run(impact_engine, moves[: i % 4])
    assert checksum(impact_engine) == before


def test_reset_equals_base(impact_engine):
    first = json.dumps(run(impact_engine), default=str, sort_keys=True)
    run(impact_engine, [Drop(fx.GAMMA_1)])
    again = json.dumps(run(impact_engine, []), default=str, sort_keys=True)
    assert first == again


def test_moves_survive_switching_selected_team(impact_engine):
    moves = [Drop(fx.GAMMA_1, team_id=GAMMAS), Add(fx.BUSY, team_id=GAMMAS)]
    as_betas = run(impact_engine, moves, team=BETAS)
    gammas = ids(as_betas, GAMMAS)
    assert fx.BUSY in gammas and fx.GAMMA_1 not in gammas
    with impact_engine.connect() as conn:
        page = list_players(conn, settings(BETAS), moves, query="gamma one")
    assert page["players"][0]["owner_label"] == "FA"
