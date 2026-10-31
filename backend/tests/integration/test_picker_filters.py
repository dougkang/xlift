"""Player picker filters and category sort (013), on the impact fixture."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from ffmodel.api.app import create_app
from ffmodel.core.scenario import Swap
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.picker import InvalidQuery, list_players
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from ffmodel.tools.player_analysis.leaderboard import leaderboard
from ffmodel.tools.player_analysis.settings import LeaderboardQuery, PlayerAnalysisSettings
from tests.fixtures import impact_dataset as fx

ALPHAS, BETAS, GAMMAS, DELTAS = 1, 2, 3, 4
CATS = ["pts", "reb", "ast", "stl", "blk", "fg3m", "fg_pct", "ft_pct", "tov"]


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def pick(engine, moves=(), team=ALPHAS, **kw):
    s = AnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY)
    with engine.connect() as conn:
        return list_players(conn, s, moves, limit=200, **kw)


def test_nothing_picked_is_todays_picker(impact_engine):  # FR-010, SC-004
    plain = pick(impact_engine)
    again = pick(impact_engine, positions=[], owners=[], sort_categories=[])
    assert again == plain
    assert all(p["sort_xlift"] is None for p in plain["players"])


def test_positions(impact_engine):  # US1, SC-001
    # The fixture's players are all guards; give a few other positions, and one none.
    with impact_engine.begin() as conn:
        for pid, pos in ((fx.BUSY, "C"), (fx.STEADY, "F,C"), (fx.BETA_1, "F"), (fx.ROOKIE, None)):
            conn.execute(
                text("UPDATE player SET positions = :p WHERE player_id = :id"),
                {"p": pos, "id": pid},
            )
    every = pick(impact_engine)["players"]
    for picked in (["C"], ["G", "C"], ["F"]):
        r = pick(impact_engine, positions=picked)["players"]
        assert r and all(set(p["positions"]) & set(picked) for p in r)
        # Same order as unfiltered.
        assert [p["player_id"] for p in r] == [
            p["player_id"] for p in every if set(p["positions"]) & set(picked)
        ]
    ids = {p["player_id"] for p in pick(impact_engine, positions=["C"])["players"]}
    assert {fx.BUSY, fx.STEADY} <= ids
    all_positions = pick(impact_engine, positions=["G", "F", "C"])["players"]
    assert fx.ROOKIE not in {p["player_id"] for p in all_positions}  # no position: unfiltered only
    assert fx.ROOKIE in {p["player_id"] for p in every}


def test_owners(impact_engine):  # US2, SC-002
    r = pick(impact_engine, owners=[BETAS, GAMMAS])["players"]
    assert r and {p["owner_team_id"] for p in r} == {BETAS, GAMMAS}
    fa = pick(impact_engine, owners=["fa"])["players"]
    assert fa and all(p["owner_team_id"] is None for p in fa)
    both = pick(impact_engine, owners=["fa", DELTAS], positions=["G"])["players"]
    assert all(p["owner_team_id"] in (None, DELTAS) and "G" in p["positions"] for p in both)
    assert pick(impact_engine, owners=[ALPHAS])["players"] == []  # your own team is never listed


def test_owner_follows_moves(impact_engine):
    trade = [Swap(acquire_id=fx.BETA_1, give_id=fx.ALPHA_1, team_id=ALPHAS)]
    r = pick(impact_engine, trade, owners=[BETAS])["players"]
    ids = {p["player_id"] for p in r}
    assert fx.ALPHA_1 in ids and fx.BETA_1 not in ids


def test_category_sort(impact_engine):  # US3, SC-003, FR-007
    r = pick(impact_engine, sort_categories=["reb", "blk"])["players"]
    scored = [p for p in r if p["sort_xlift"] is not None]
    assert scored
    for group in (True, False):  # free agents first, each group in non-increasing order
        vals = [p["sort_xlift"] for p in scored if (p["owner_team_id"] is None) == group]
        assert vals == sorted(vals, reverse=True)
    s = PlayerAnalysisSettings(league_id=1, team_id=ALPHAS, as_of=fx.IMPACT_TODAY)
    with impact_engine.connect() as conn:
        board = leaderboard(conn, s, LeaderboardQuery(pool="all", top=None, min_games=1))
    by_cat = {e["player_id"]: e["by_category"] for e in board["entries"]}
    i, j = CATS.index("reb"), CATS.index("blk")
    for p in scored:
        if p["player_id"] in by_cat and p["owner_team_id"] != ALPHAS:
            assert p["sort_xlift"] == pytest.approx(
                by_cat[p["player_id"]][i] + by_cat[p["player_id"]][j], abs=0.01
            )
    # The total stays the total.
    totals = {p["player_id"]: p["xlift"] for p in pick(impact_engine)["players"]}
    assert all(p["xlift"] == totals[p["player_id"]] for p in r)


def test_turnovers_count_fewer_as_a_gain(impact_engine):
    r = pick(impact_engine, sort_categories=["tov"])["players"]
    s = PlayerAnalysisSettings(league_id=1, team_id=ALPHAS, as_of=fx.IMPACT_TODAY)
    with impact_engine.connect() as conn:
        board = leaderboard(conn, s, LeaderboardQuery(pool="all", top=None, min_games=1))
    by_cat = {e["player_id"]: e["by_category"][CATS.index("tov")] for e in board["entries"]}
    for p in r:
        if p["sort_xlift"] is not None and p["player_id"] in by_cat:
            assert p["sort_xlift"] == pytest.approx(by_cat[p["player_id"]], abs=1e-9)


def test_unknown_category(impact_engine):
    with pytest.raises(InvalidQuery):
        pick(impact_engine, sort_categories=["dunks"])
    client = TestClient(create_app(impact_engine))
    body = {"league_id": 1, "team_id": ALPHAS, "as_of": fx.IMPACT_TODAY.isoformat()}
    assert (
        client.post("/api/impact/players", json={**body, "sort_categories": ["dunks"]}).status_code
        == 422
    )
    assert client.post("/api/impact/players", json={**body, "positions": ["X"]}).status_code == 422
    ok = client.post(
        "/api/impact/players",
        json={**body, "positions": ["C"], "owners": ["fa", 2], "sort_categories": ["reb"]},
    )
    assert ok.status_code == 200
