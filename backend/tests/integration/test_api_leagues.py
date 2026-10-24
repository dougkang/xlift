import pytest
from fastapi.testclient import TestClient

from ffmodel.api.app import create_app


@pytest.fixture
def client(impact_engine):
    return TestClient(create_app(impact_engine))


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "schema_version": 2}


def test_leagues(client):
    (league,) = client.get("/api/leagues").json()
    assert league["league_key"] == "impact-league" and league["team_count"] == 4


def test_league_detail(client):
    body = client.get("/api/leagues/1").json()
    assert [t["name"] for t in body["teams"]] == ["Alphas", "Betas", "Gammas", "Deltas"]
    assert body["teams"][2]["manager"] == "Cy"
    assert body["freshness"] == {
        "nba_data_loaded_at": "2026-11-18T08:00:00+00:00",
        "roster_as_of": "2026-11-18",
        "matchup_as_of": None,
    }
    assert body["current_matchup"] is None  # no matchups.csv imported


def test_league_detail_with_matchup(impact_engine, client):
    from tests.fixtures.impact_dataset import load_matchup_state

    with impact_engine.begin() as conn:
        load_matchup_state(conn)
    body = client.get("/api/leagues/1").json()
    cm = body["current_matchup"]
    assert (cm["week"], cm["period_start"], cm["period_end"], cm["as_of"]) == (
        1,
        "2026-11-16",
        "2026-11-22",
        "2026-11-17",
    )
    assert body["freshness"]["matchup_as_of"] == "2026-11-17"


def test_unknown_league(client):
    assert client.get("/api/leagues/99").status_code == 404
