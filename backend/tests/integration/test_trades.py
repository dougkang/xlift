"""The Trade Finder (014), on the impact fixture."""

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from ffmodel.api.app import create_app
from ffmodel.api.schemas import TradesResult
from ffmodel.core import cache as core_cache
from ffmodel.core.data import get_league
from ffmodel.core.model import fragility
from ffmodel.core.scenario import from_snapshot
from ffmodel.core.scoring import get_format
from ffmodel.core.value import expected_wins, lines, team_keys, team_totals, trade_grid
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.player_analysis.leaderboard import NotFound
from ffmodel.tools.player_analysis.settings import PlayerAnalysisSettings, normalize
from ffmodel.tools.player_analysis.trades import find_trades
from tests.fixtures import impact_dataset as fx

FMT = get_format("9cat_h2h")


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


@pytest.fixture
def complementary(impact_engine):
    """Give the Alphas a pure shooter and the Betas a big rebounder, so their needs differ enough
    for a win-win (the plain fixture's teams are all similar guards)."""
    with impact_engine.begin() as conn:
        conn.execute(
            text("UPDATE player_game SET fg3m = fgm, fg3a = fga WHERE player_id = :p"),
            {"p": fx.ALPHA_1},
        )
        conn.execute(
            text(
                "UPDATE player_game SET dreb = dreb * 3, reb = oreb + dreb * 3 WHERE player_id = :p"
            ),
            {"p": fx.BETA_1},
        )
    cache.clear()
    return impact_engine


def settings(team=1, **kw):
    return PlayerAnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, **kw)


def run(engine, team=1, **kw):
    with engine.connect() as conn:
        r = find_trades(conn, settings(team, **kw))
    TradesResult.model_validate(r)
    return r


def inputs(engine, team=1):
    """The scenario, projections and spread find_trades uses, rebuilt independently."""
    s = normalize(settings(team))
    with engine.connect() as conn:
        snap = get_league(conn, 1)
        scenario = from_snapshot(snap)
        roster = {r.player.player_id: r.status for t in snap.teams for r in t.roster}

        def penalize(proj, sc):
            return fragility.apply(s.fragility, proj, sc, roster, conn, s.as_of)

        proj = penalize(core_cache.projections(conn, list(roster), FMT, s), scenario)
        spread = core_cache.league_spread(conn, FMT, s, snap, penalize)
    return scenario, proj, spread, s


def test_similar_teams_find_no_win_win(impact_engine):  # FR-006
    r = run(impact_engine)
    assert len(r["rows"]) == 3 and all(row["trade"] is None for row in r["rows"])


@pytest.mark.parametrize("team", [1, 2])
def test_one_row_per_other_team_and_win_wins(complementary, team):  # US1, SC-001
    r = run(complementary, team)
    assert sorted(row["team_id"] for row in r["rows"]) == [t for t in (1, 2, 3, 4) if t != team]
    shown = [row["trade"] for row in r["rows"] if row["trade"]]
    assert shown, "the Alphas and Betas should find a win-win"
    for t in shown:
        assert round(t["your_gain"], 2) > 0 and round(t["their_gain"], 2) > 0
        # Every category in the format's order, summing to your gain.
        assert [c["category"] for c in t["your_categories"]] == [c["key"] for c in r["categories"]]
        assert sum(c["gain"] for c in t["your_categories"]) == pytest.approx(t["your_gain"])
    # Order: the smaller gain, largest first; no-trade rows last.
    keys = [
        min(row["trade"]["your_gain"], row["trade"]["their_gain"])
        for row in r["rows"]
        if row["trade"]
    ]
    assert keys == sorted(keys, reverse=True)
    seen_none = False
    for row in r["rows"]:
        seen_none |= row["trade"] is None
        assert not (seen_none and row["trade"])


def test_the_pick_is_the_most_balanced(complementary):  # FR-003, SC-002
    r = run(complementary)
    scenario, proj, spread, s = inputs(complementary)
    assert any(row["trade"] for row in r["rows"])
    for row in r["rows"]:
        mine, theirs, ga, gb, _ = trade_grid(
            scenario, 1, row["team_id"], proj, FMT, s.games_per_period, spread
        )
        both = (ga >= 0.005) & (gb >= 0.005)
        if not both.any():
            assert row["trade"] is None
            continue
        best = np.max(np.where(both, np.minimum(ga, gb), -np.inf))
        t = row["trade"]
        assert min(t["your_gain"], t["their_gain"]) == pytest.approx(best)
        assert t["give"]["player_id"] in mine and t["get"]["player_id"] in theirs


def test_gain_is_the_change_in_expected_wins(complementary):  # SC-003
    r = run(complementary)
    scenario, proj, spread, s = inputs(complementary)
    pl = lines(proj, s.games_per_period)
    ids, T = team_totals(scenario, pl, FMT.base_stats)
    for row in r["rows"]:
        t = row["trade"]
        if not t:
            continue
        a, b = ids.index(1), ids.index(row["team_id"])
        give, get = pl[t["give"]["player_id"]], pl[t["get"]["player_id"]]
        new = T.copy()
        new[a], new[b] = T[a] - give + get, T[b] - get + give
        K, Kn = team_keys(T, FMT), team_keys(new, FMT)
        assert t["your_gain"] == pytest.approx(
            expected_wins(a, Kn, spread) - expected_wins(a, K, spread), abs=0.01
        )
        assert t["their_gain"] == pytest.approx(
            expected_wins(b, Kn, spread) - expected_wins(b, K, spread), abs=0.01
        )


def test_active_players_only(complementary):
    scenario, *_ = inputs(complementary)
    for row in run(complementary)["rows"]:
        if row["trade"]:
            assert row["trade"]["give"]["player_id"] in scenario.active_players(1)
            assert row["trade"]["get"]["player_id"] in scenario.active_players(row["team_id"])


def test_not_found(impact_engine):
    with pytest.raises(NotFound):
        run(impact_engine, team=99)
    client = TestClient(create_app(impact_engine))
    url = "/api/player-analysis/trades"
    assert client.post(url, json={"league_id": 9, "team_id": 1}).status_code == 404
    ok = client.post(url, json={"league_id": 1, "team_id": 1, "as_of": fx.IMPACT_TODAY.isoformat()})
    assert ok.status_code == 200 and len(ok.json()["rows"]) == 3
