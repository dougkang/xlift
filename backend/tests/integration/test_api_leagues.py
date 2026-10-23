import pytest
from fastapi.testclient import TestClient

from ffmodel.api.app import create_app


@pytest.fixture
def client(impact_engine):
    return TestClient(create_app(impact_engine))


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "schema_version": 1}


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
    }


def test_unknown_league(client):
    assert client.get("/api/leagues/99").status_code == 404
