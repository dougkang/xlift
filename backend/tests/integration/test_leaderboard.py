"""The xLift leaderboard (009), on the impact fixture."""

import json

import pytest

from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.picker import list_players
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from ffmodel.tools.player_analysis.leaderboard import leaderboard
from ffmodel.tools.player_analysis.settings import LeaderboardQuery, PlayerAnalysisSettings
from tests.fixtures import impact_dataset as fx
from tests.integration.test_pre009_snapshot import PRE009, impact_numbers
from tests.pre010 import strip_010

ALPHAS, GAMMAS = 1, 3
FREE_AGENTS = {fx.STEADY, fx.BUSY, fx.ROOKIE, fx.BENCH}


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def board(engine, team=ALPHAS, fragility="dab_tag", **query):
    s = PlayerAnalysisSettings(
        league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, fragility=fragility
    )
    q = LeaderboardQuery(**({"min_games": 1} | query))
    with engine.connect() as conn:
        return leaderboard(conn, s, q)


def picker_xlift(engine, team=ALPHAS, fragility="dab_tag"):
    s = AnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, fragility=fragility)
    with engine.connect() as conn:
        rows = list_players(conn, s, limit=200)["players"]
    return {r["player_id"]: r["xlift"] for r in rows}


def assert_ordered(entries):
    keys = [(-e["xlift"], e["name"], e["player_id"]) for e in entries]
    assert keys == sorted(keys)


# --- US1 --------------------------------------------------------------------------------------


def test_free_agents_ranked_for_the_team(impact_engine):
    r = board(impact_engine)
    ids = [e["player_id"] for e in r["entries"]]
    assert ids and set(ids) <= FREE_AGENTS
    assert all(
        e["owner_team_id"] is None and e["owner_label"] == "Free agent" for e in r["entries"]
    )
    assert_ordered(r["entries"])
    assert r["total"] == len(ids)
    assert r["settings"]["mode"] == "strategic"
    assert r["evaluate_for"] == "team" and r["team_id"] == ALPHAS and r["team_name"] == "Alphas"
    assert [c["key"] for c in r["categories"]][-1] == "tov"
    assert r["categories"][-1]["higher_is_better"] is False


def test_categories_sum_to_the_net(impact_engine):
    for team in (ALPHAS, GAMMAS):
        r = board(impact_engine, team=team, pool="all")
        for e in r["entries"]:
            assert len(e["by_category"]) == len(r["categories"])
            assert sum(e["by_category"]) == pytest.approx(e["xlift"], abs=0.01)


@pytest.mark.parametrize("fragility", ["dab_tag", "last15", "none"])
@pytest.mark.parametrize("team", [ALPHAS, GAMMAS])
def test_team_values_equal_the_strategic_picker(impact_engine, team, fragility):
    """SC-001: the leaderboard's Your team values are the picker's."""
    r = board(impact_engine, team=team, fragility=fragility, pool="all")
    picked = picker_xlift(impact_engine, team=team, fragility=fragility)
    assert r["entries"]
    for e in r["entries"]:
        assert e["xlift"] == pytest.approx(picked[e["player_id"]], abs=0.005)


def test_footnote_marks_short_projections(impact_engine):
    for e in board(impact_engine, pool="all")["entries"]:
        short = e["games_found"] < e["games_requested"]
        want = f"* {e['games_found']} of {e['games_requested']} games" if short else None
        assert e["footnote"] == want


def test_impact_analysis_is_unchanged(impact_engine):
    """SC-007: Impact Analysis reproduces its pre-009 numbers exactly."""
    with impact_engine.connect() as conn:
        assert strip_010(impact_numbers(conn)) == json.loads(PRE009.read_text())


def test_unknown_team_is_not_found(impact_engine):
    from ffmodel.tools.player_analysis.leaderboard import NotFound

    with pytest.raises(NotFound):
        board(impact_engine, team=99)


# --- US2 --------------------------------------------------------------------------------------


def test_all_players_adds_other_teams_but_never_your_own(impact_engine):
    r = board(impact_engine, pool="all")
    owners = {e["owner_team_id"] for e in r["entries"]}
    assert None in owners and owners - {None}
    assert ALPHAS not in owners
    names = {2: "Betas", 3: "Gammas", 4: "Deltas"}
    for e in r["entries"]:
        if e["owner_team_id"] is not None:
            assert e["owner_label"] == names[e["owner_team_id"]]
    assert_ordered(r["entries"])


def test_one_teams_players(impact_engine):
    """A team as the pool lists only that team's players, scored the same as under All players."""
    every = {e["player_id"]: e for e in board(impact_engine, pool="all")["entries"]}
    r = board(impact_engine, pool=GAMMAS)
    assert r["entries"] and {e["owner_team_id"] for e in r["entries"]} == {GAMMAS}
    for e in r["entries"]:
        assert e["xlift"] == every[e["player_id"]]["xlift"]
    assert_ordered(r["entries"])


def test_own_team_as_the_pool(impact_engine):
    """Under Your team, your own players are the team being scored, so none are listed; under
    League they're scored for every other team."""
    assert board(impact_engine, pool=ALPHAS)["entries"] == []
    league = board(impact_engine, pool=ALPHAS, evaluate_for="league")
    assert league["entries"] and {e["owner_team_id"] for e in league["entries"]} == {ALPHAS}


def test_unknown_pool_team_is_not_found(impact_engine):
    from ffmodel.tools.player_analysis.leaderboard import NotFound

    with pytest.raises(NotFound):
        board(impact_engine, pool=99)


def test_top_keeps_the_head_of_the_order(impact_engine):
    full = board(impact_engine, pool="all", top=None)
    head = board(impact_engine, pool="all", top=3)
    assert len(head["entries"]) == 3 and head["total"] == full["total"] > 3
    assert head["entries"] == full["entries"][:3]


def test_min_games_hides_short_projections(impact_engine):
    full = board(impact_engine, pool="all", top=None)
    games = sorted({e["games_found"] for e in full["entries"]})
    cut = games[-1]
    kept = board(impact_engine, pool="all", top=None, min_games=cut)["entries"]
    assert kept and all(e["games_found"] >= cut for e in kept)
    assert len(kept) == sum(e["games_found"] >= cut for e in full["entries"])
    none = board(impact_engine, pool="all", top=None, min_games=cut + 1)
    assert none["entries"] == [] and none["total"] == 0


def test_league_scope(impact_engine):
    a = board(impact_engine, team=ALPHAS, evaluate_for="league", pool="all", top=None)
    g = board(impact_engine, team=GAMMAS, evaluate_for="league", pool="all", top=None)
    assert a["evaluate_for"] == "league"
    # The selected team's players are listed, and the selected team doesn't change any value.
    assert ALPHAS in {e["owner_team_id"] for e in a["entries"]}
    assert [(e["player_id"], e["xlift"]) for e in a["entries"]] == [
        (e["player_id"], e["xlift"]) for e in g["entries"]
    ]
    for e in a["entries"]:
        assert sum(e["by_category"]) == pytest.approx(e["xlift"], abs=0.01)
    assert_ordered(a["entries"])
    # Position-neutral differs from one team's view.
    team = {e["player_id"]: e["xlift"] for e in board(impact_engine, team=ALPHAS)["entries"]}
    league = {e["player_id"]: e["xlift"] for e in a["entries"]}
    assert any(abs(team[p] - league[p]) > 1e-6 for p in team)
