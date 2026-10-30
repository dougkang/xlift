"""POST /api/player-analysis/leaderboard (009 contracts/api.md)."""

import pytest
from fastapi.testclient import TestClient

from ffmodel.api.app import create_app
from ffmodel.tools.impact_analysis import cache

ALPHAS = {"league_id": 1, "team_id": 1, "as_of": "2026-11-18"}
URL = "/api/player-analysis/leaderboard"


@pytest.fixture
def client(impact_engine):
    cache.clear()
    return TestClient(create_app(impact_engine))


def test_shape(client):
    r = client.post(URL, json=ALPHAS | {"min_games": 1, "top": 10})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "settings",
        "evaluate_for",
        "team_id",
        "team_name",
        "categories",
        "total",
        "entries",
        "warnings",
    }
    assert body["settings"] == {
        "mode": "strategic",
        "window": 82,
        "as_of": "2026-11-18",
        "fragility": "dab_tag",
    }
    assert set(body["categories"][0]) == {"key", "label", "higher_is_better"}
    assert body["entries"] and set(body["entries"][0]) == {
        "player_id",
        "name",
        "nba_team",
        "owner_team_id",
        "owner_label",
        "status",
        "games_found",
        "games_requested",
        "footnote",
        "xlift",
        "by_category",
    }
    assert body["warnings"] == []


@pytest.mark.parametrize("body", [{"league_id": 99}, {"team_id": 99}])
def test_not_found(client, body):
    assert client.post(URL, json=ALPHAS | body).status_code == 404


@pytest.mark.parametrize(
    "bad",
    [
        {"window": 0},
        {"window": 83},
        {"top": 12},
        {"top": 5},
        {"top": 55},
        {"min_games": 0},
        {"min_games": 16},
        {"fragility": "sometimes"},
        {"evaluate_for": "opponent"},
        {"pool": "bench"},
    ],
)
def test_validation(client, bad):
    assert client.post(URL, json=ALPHAS | bad).status_code == 422


def test_team_pool(client):
    r = client.post(URL, json=ALPHAS | {"pool": 3, "min_games": 1})
    assert r.status_code == 200
    assert {e["owner_team_id"] for e in r.json()["entries"]} == {3}
    assert client.post(URL, json=ALPHAS | {"pool": 99}).status_code == 404
