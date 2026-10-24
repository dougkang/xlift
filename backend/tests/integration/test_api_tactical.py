"""Tactical over HTTP (005): every result shape, including each warning, passes the API schema."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from ffmodel.api.app import create_app
from ffmodel.tools.impact_analysis import cache
from tests.fixtures import impact_dataset as fx

BODY = {
    "league_id": 1,
    "team_id": 3,
    "mode": "tactical",
    "as_of": fx.IMPACT_TODAY.isoformat(),
    "iterations": 2000,
}


@pytest.fixture
def client(impact_engine):
    cache.clear()
    return TestClient(create_app(impact_engine))


def codes(res):
    assert res.status_code == 200, res.text
    return [w["code"] for w in res.json()["warnings"]]


def test_not_loaded(client):
    assert codes(client.post("/api/impact/analyze", json=BODY)) == ["MATCHUP_NOT_LOADED"]


def test_current_matchup_with_date_and_stale_warnings(impact_engine, client):
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn)  # as of 11-17; rosters are from 11-18
        conn.execute(text("UPDATE game SET status = 'final' WHERE game_date = '2026-11-18'"))
    res = client.post("/api/impact/analyze", json=BODY)
    assert set(codes(res)) == {"MATCHUP_STALE", "ROSTER_MATCHUP_DATES_DIFFER"}
    body = res.json()
    assert body["header"]["matchup"]["opponent_name"] == "Deltas"
    assert body["category_table"]["rows"][0]["selected_actual"] is not None


def test_final_week(impact_engine, client):
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn, as_of=fx.WEEK[1])
    res = client.post("/api/impact/analyze", json=BODY)
    assert "NO_GAMES_REMAINING" in codes(res)
    assert res.json()["header"]["matchup"]["final"] is True


def test_moves_in_tactical(impact_engine, client):
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn)
    move = {"type": "drop", "player_id": fx.GAMMA_1, "team_id": 3}
    res = client.post("/api/impact/analyze", json=BODY | {"moves": [move]})
    assert res.status_code == 200, res.text
    assert res.json()["changes"]["matchup_totals"] is None
