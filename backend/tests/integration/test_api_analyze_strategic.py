import pytest
from fastapi.testclient import TestClient

from ffmodel.api.app import create_app
from ffmodel.tools.impact_analysis import cache

BODY = {"league_id": 1, "team_id": 1, "as_of": "2026-11-18"}


@pytest.fixture
def client(impact_engine):
    cache.clear()
    return TestClient(create_app(impact_engine))


def test_analyze_shape_and_echo(client):
    r = client.post("/api/impact/analyze", json=BODY)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["settings"] | {} == body["settings"]
    assert body["settings"]["as_of"] == "2026-11-18"
    assert body["settings"]["seed"] == 20261023 and body["settings"]["iterations"] == 10000
    assert body["header"]["record"]["unit"] == "matchups"
    assert len(body["radar"]["series"]) == 4 and len(body["curves"]) == 9


@pytest.mark.parametrize(
    "bad",
    [
        {"window": 0},
        {"window": 83},
        {"iterations": 500},
        {"opponent_id": 1},
        {"period_start": "2026-11-20", "period_end": "2026-11-19"},
    ],
)
def test_bad_settings(client, bad):
    assert client.post("/api/impact/analyze", json=BODY | bad).status_code == 422


def test_unknown_team_and_league(client):
    assert client.post("/api/impact/analyze", json=BODY | {"team_id": 99}).status_code == 404
    assert client.post("/api/impact/analyze", json=BODY | {"league_id": 99}).status_code == 404
