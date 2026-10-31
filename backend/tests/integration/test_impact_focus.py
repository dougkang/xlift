"""Focus on an H2H opponent (011): the radar, table and curves compare with one opponent."""

import pytest
from fastapi.testclient import TestClient

from ffmodel.api.app import create_app
from ffmodel.api.schemas import AnalysisResult
from ffmodel.core.scenario import Drop, Swap
from ffmodel.tools.impact_analysis import analysis, cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

ALPHAS, BETAS, GAMMAS, DELTAS = 1, 2, 3, 4
TRADE = [Swap(acquire_id=fx.ALPHA_1, give_id=fx.DELTA_1, team_id=DELTAS)]


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def run(engine, focus=None, moves=(), team=DELTAS, mode="strategic"):
    with engine.connect() as conn:
        r = analyze(
            conn,
            AnalysisSettings(
                league_id=1,
                team_id=team,
                mode=mode,
                as_of=fx.IMPACT_TODAY,
                iterations=2000,
                focus_opponent_id=focus,
            ),
            moves,
        )
    AnalysisResult.model_validate(r)
    return r


def chances(r, opp):
    row = next(m for m in r["matchups"] if m["opponent_id"] == opp)
    return [row["categories"][c["key"]] for c in r["categories"]]


def test_focused_view(impact_engine):  # FR-005..FR-008, SC-001, SC-002
    plain, r = run(impact_engine), run(impact_engine, focus=ALPHAS)
    assert r["focus"] == {"opponent_id": ALPHAS, "opponent_name": "Alphas"}
    assert r["settings"]["focus_opponent_id"] == ALPHAS
    series = r["radar"]["series"]
    assert [(s["team_id"], s["emphasis"]) for s in series] == [
        (ALPHAS, "opponent"),
        (DELTAS, "selected"),
    ]
    assert r["radar"]["league"] == []
    mine = [o["win"] + 0.5 * o["tie"] for o in chances(r, ALPHAS)]
    assert series[1]["win_rate"] == pytest.approx(mine)
    assert series[0]["win_rate"] == pytest.approx([1 - m for m in mine])
    alphas = next(s for s in plain["radar"]["series"] if s["team_id"] == ALPHAS)
    for i, row in enumerate(r["category_table"]["rows"]):
        assert row["league_average"] == alphas["averages"][i]
        assert row["win_rate"] == pytest.approx(mine[i])
    for i, curve in enumerate(r["curves"]):
        roles = {s["role"]: s for s in curve["series"]}
        assert "league_average" not in roles
        assert roles["opponent"]["label"] == "Alphas"
        assert roles["opponent"]["mean"] == r["category_table"]["rows"][i]["league_average"]
        leader = roles.get("leader") or roles.get("next_best")
        if leader is not None:
            assert leader["team_id"] != ALPHAS  # drawn once, as the opponent


def test_leader_kept_unless_it_is_the_opponent(impact_engine):  # FR-008 (clarified)
    plain = run(impact_engine)
    shown = {}  # category -> the leader or next best curve's team, unfocused
    for curve in plain["curves"]:
        lead = next(x for x in curve["series"] if x["role"] in ("leader", "next_best"))
        shown[curve["category"]] = (lead["role"], lead["team_id"])
    hits = 0
    for other in (ALPHAS, BETAS, GAMMAS):
        r = run(impact_engine, focus=other)
        for curve in r["curves"]:
            roles = {x["role"]: x for x in curve["series"]}
            role, team = shown[curve["category"]]
            if team == other:
                assert role not in roles  # drawn once, as the opponent
                hits += 1
            else:
                assert roles[role]["team_id"] == team
    assert hits  # some opponent leads some category in the fixture


def test_selected_team_and_league_parts_unchanged(impact_engine):  # FR-009, FR-010, SC-005
    plain, r = run(impact_engine), run(impact_engine, focus=GAMMAS)
    for key in ("header", "matchups", "matchup_totals", "rosters", "league_shape", "footnotes"):
        assert r[key] == plain[key], key
    me = next(s for s in plain["radar"]["series"] if s["team_id"] == DELTAS)
    me_f = next(s for s in r["radar"]["series"] if s["team_id"] == DELTAS)
    for key in ("ranks", "normalized", "area", "averages"):
        assert me_f[key] == me[key], key
    assert me_f["win_rate"] != me["win_rate"]  # the one number that becomes the matchup's
    for row, row_f in zip(
        plain["category_table"]["rows"], r["category_table"]["rows"], strict=True
    ):
        for key in ("rank", "average", "leader_team_id", "leader_name", "leader_average"):
            assert row_f[key] == row[key], key
    sel = [next(s for s in c["series"] if s["role"] == "selected") for c in plain["curves"]]
    sel_f = [next(s for s in c["series"] if s["role"] == "selected") for c in r["curves"]]
    assert [s["mean"] for s in sel_f] == [s["mean"] for s in sel]


def test_clearing_focus_restores_the_league_view(impact_engine):  # SC-004
    fresh = run(impact_engine)
    run(impact_engine, focus=ALPHAS)
    again = run(impact_engine)
    assert again == fresh


def test_tactical_ignores_focus(impact_engine):
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn, as_of=fx.IMPACT_TODAY)
    r = run(impact_engine, focus=ALPHAS, team=GAMMAS, mode="tactical")
    assert r["focus"] is None and r["settings"]["focus_opponent_id"] is None


def test_api_validates_focus(impact_engine):
    client = TestClient(create_app(impact_engine))
    body = {"league_id": 1, "team_id": DELTAS, "as_of": fx.IMPACT_TODAY.isoformat()}
    assert (
        client.post("/api/impact/analyze", json={**body, "focus_opponent_id": 99}).status_code
        == 404
    )
    own = client.post("/api/impact/analyze", json={**body, "focus_opponent_id": DELTAS})
    assert own.status_code == 422
    ok = client.post(
        "/api/impact/analyze", json={**body, "iterations": 1000, "focus_opponent_id": ALPHAS}
    )
    assert ok.status_code == 200 and ok.json()["focus"]["opponent_id"] == ALPHAS


def test_moves_under_focus(impact_engine):  # US3, FR-004 (backend side)
    r = run(impact_engine, focus=BETAS, moves=[Drop(fx.DELTA_1)])
    ch = r["changes"]
    assert ch is not None
    assert all(any(s["role"] == "selected_original" for s in c["series"]) for c in r["curves"])
    assert [o["team_id"] for o in ch["radar"]["original"]] == [DELTAS]  # Betas untouched


def test_trade_with_the_focused_opponent(impact_engine):  # US3 AS3, R4
    before, after = run(impact_engine, focus=ALPHAS), run(impact_engine, focus=ALPHAS, moves=TRADE)
    assert [o["team_id"] for o in after["changes"]["radar"]["original"]] == [DELTAS, ALPHAS]
    assert str(ALPHAS) in after["changes"]["radar"]["tones"]
    assert [r["league_average"] for r in after["category_table"]["rows"]] != [
        r["league_average"] for r in before["category_table"]["rows"]
    ]
    cats = {c["key"]: c for c in after["categories"]}
    for key, ch in after["changes"]["category_table"].items():
        la = ch["league_average"]
        if la is not None:  # the opponent getting better is worse for you
            better_for_them = (la["delta"] > 0) == cats[key]["higher_is_better"]
            assert la["tone"] == ("worse" if better_for_them else "better"), key


def test_focus_change_does_not_resimulate(impact_engine, monkeypatch):  # SC-003, R2
    calls = {"n": 0}
    real = analysis._compute

    def counting(*args, **kw):
        calls["n"] += 1
        return real(*args, **kw)

    monkeypatch.setattr(analysis, "_compute", counting)
    run(impact_engine, moves=TRADE)
    n = calls["n"]  # the original and the moved scenario
    run(impact_engine, focus=ALPHAS, moves=TRADE)
    run(impact_engine, focus=BETAS, moves=TRADE)
    run(impact_engine, focus=None, moves=TRADE)
    assert calls["n"] == n == 2
