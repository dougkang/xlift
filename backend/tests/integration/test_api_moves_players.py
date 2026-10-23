import pytest
from fastapi.testclient import TestClient

from ffmodel.api.app import create_app
from ffmodel.tools.impact_analysis import cache
from tests.fixtures import impact_dataset as fx

GAMMAS = {"league_id": 1, "team_id": 3, "as_of": "2026-11-18", "iterations": 2000}
ALPHAS = GAMMAS | {"team_id": 1}


@pytest.fixture
def client(impact_engine):
    cache.clear()
    return TestClient(create_app(impact_engine))


def test_invalid_move_is_422_with_index(client):
    body = GAMMAS | {
        "moves": [{"type": "add", "player_id": fx.BUSY}, {"type": "add", "player_id": fx.STEADY}]
    }
    r = client.post("/api/impact/analyze", json=body)
    assert r.status_code == 422
    assert r.json()["detail"] == {
        "move_index": 1,
        "code": "NO_ACTIVE_SLOT",
        "message": "Gammas has no open active slot",
    }


def test_moves_applied_in_analyze(client):
    body = GAMMAS | {"moves": [{"type": "swap", "acquire_id": fx.ALPHA_1, "give_id": fx.GAMMA_2}]}
    r = client.post("/api/impact/analyze", json=body).json()
    gammas = next(t for t in r["rosters"] if t["team_id"] == 3)
    assert fx.ALPHA_1 in {p["player_id"] for p in gammas["players"]}


def players(client, body, **extra):
    r = client.post("/api/impact/players", json=body | extra)
    assert r.status_code == 200, r.text
    return r.json()


def by_name(page):
    return {p["name"]: p for p in page["players"]}


def test_eligibility_with_open_slot(client):
    page = players(client, GAMMAS, limit=200)
    rows = by_name(page)
    assert rows["Busy Streamer"]["eligibility"] == {
        "can_add": True,
        "add_blocked_reason": None,
        "swap_give_options": [],
    }
    alpha = rows["Alpha One"]["eligibility"]
    assert not alpha["can_add"] and alpha["add_blocked_reason"] == "On Alphas: swap required"
    assert alpha["swap_give_options"] == ["roster", "free_agent"]
    owners = [p["owner_label"] for p in page["players"]]
    first_rostered = next(i for i, o in enumerate(owners) if o != "FA")
    assert all(o == "FA" for o in owners[:first_rostered])
    assert all(o != "FA" for o in owners[first_rostered:])
    assert "Gamma One" not in rows  # own team excluded


def test_eligibility_full_roster(client):
    rows = by_name(players(client, ALPHAS, limit=200))
    fa = rows["Busy Streamer"]["eligibility"]
    assert not fa["can_add"] and fa["add_blocked_reason"].startswith("No open active slot")
    assert rows["Beta One"]["eligibility"]["swap_give_options"] == ["roster"]


def test_search_and_paging(client):
    assert {p["name"] for p in players(client, GAMMAS, query="streamer")["players"]} == {
        "Busy Streamer",
        "Steady Streamer",
    }
    assert [p["name"] for p in players(client, GAMMAS, query="busy strea")["players"]] == [
        "Busy Streamer"
    ]
    full = players(client, GAMMAS, limit=200)
    page2 = players(client, GAMMAS, limit=3, offset=3)
    assert page2["total"] == full["total"]
    assert [p["name"] for p in page2["players"]] == [p["name"] for p in full["players"][3:6]]


def test_free_agents_only_and_footnote(client):
    page = players(client, GAMMAS, free_agents_only=True, limit=200)
    assert {p["owner_label"] for p in page["players"]} == {"FA"}
    rookie = by_name(page)["Rookie Ray"]
    assert rookie["footnote"] == "* 2 of 15 games" and rookie["status"] == "Q"
