"""League shape in the strategic Category Breakdown (008), on the impact fixture."""

import pytest

from ffmodel.api.schemas import AnalysisResult
from ffmodel.core.scenario import Swap
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

ALPHAS, DELTAS = 1, 4


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def run(engine, team=ALPHAS, moves=(), **kw):
    with engine.connect() as conn:
        return analyze(
            conn,
            AnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, **kw),
            moves,
        )


def test_one_shape_per_category_in_order(impact_engine):
    r = run(impact_engine)
    assert [s["category"] for s in r["league_shape"]] == [c["key"] for c in r["categories"]]
    AnalysisResult.model_validate(r)


@pytest.mark.parametrize("team", [ALPHAS, DELTAS])
def test_places_ranks_and_values_match_the_analysis(impact_engine, team):
    r = run(impact_engine, team)
    radar = {s["team_id"]: s for s in r["radar"]["series"]}
    table = {row["category"]: row for row in r["category_table"]["rows"]}
    for i, shape in enumerate(r["league_shape"]):
        teams = shape["teams"]
        assert [t["place"] for t in teams] == list(range(1, len(teams) + 1))
        for t in teams:
            assert t["rank"] == radar[t["team_id"]]["ranks"][i]
            assert t["value"] == pytest.approx(radar[t["team_id"]]["averages"][i])
        mine = [t for t in teams if t["selected"]]
        assert len(mine) == 1 and mine[0]["team_id"] == team
        assert mine[0]["rank"] == table[shape["category"]]["rank"]


def test_climb_and_cushion_marks(impact_engine):
    seen_first = seen_last = False
    for team in (1, 2, 3, 4):
        for shape in run(impact_engine, team)["league_shape"]:
            n = len(shape["teams"])
            place = next(t["place"] for t in shape["teams"] if t["selected"])
            marks = {g["to_place"]: g["mark"] for g in shape["gaps"] if g["mark"]}
            want = {}
            if place > 1:
                want[place - 1] = "climb"
            if place < n:
                want[place] = "cushion"
            assert marks == want
            seen_first |= place == 1
            seen_last |= place == n
    assert seen_first and seen_last  # both edge cases occurred


def test_tactical_has_no_league_shape(impact_engine):
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn)
    cache.clear()
    r = run(impact_engine, mode="tactical", iterations=2000)
    assert r["league_shape"] is None


# --- Moves (US3) ------------------------------------------------------------------------------

MOVE = [Swap(acquire_id=fx.ALPHA_1, give_id=fx.DELTA_1)]


def test_no_before_without_moves(impact_engine):
    assert all(s["before"] is None for s in run(impact_engine, DELTAS)["league_shape"])


def test_before_marks_the_pre_move_position(impact_engine):
    original = run(impact_engine, DELTAS)
    moved = run(impact_engine, DELTAS, MOVE)
    changed = False
    for orig, now in zip(original["league_shape"], moved["league_shape"], strict=True):
        was = next(t for t in orig["teams"] if t["selected"])
        assert now["before"] == {"place": was["place"], "rank": was["rank"], "value": was["value"]}
        is_now = next(t for t in now["teams"] if t["selected"])
        changed |= is_now["value"] != was["value"]
    assert changed  # the moved league's values are shown
