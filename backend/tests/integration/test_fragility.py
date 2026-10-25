"""The Fragility Penalty (007 US3) on the impact fixture."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ffmodel.api.app import create_app
from ffmodel.core.model import availability as av
from ffmodel.core.scoring import get_format
from ffmodel.tools.impact_analysis import cache, fragility
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from ffmodel.tools.impact_analysis.state import load_state
from tests.fixtures import impact_dataset as fx

PRE007 = Path(__file__).resolve().parents[1] / "fixtures" / "pre007_strategic.json"
FMT = get_format("9cat_h2h")


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def settings(team=1, **kw):
    return AnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, **kw)


def normalized(obj):
    return json.loads(json.dumps(obj, default=str, sort_keys=True))


def test_last15_reproduces_pre_feature_results(impact_engine):
    """SC-004: results recorded from the pre-feature code, compared exactly."""
    want = json.loads(PRE007.read_text())
    with impact_engine.connect() as conn:
        for team in (1, 4):
            r = analyze(conn, settings(team, fragility="last15"))
            got = {k: r[k] for k in ("header", "matchups", "category_table", "radar", "curves")}
            assert normalized(got) == want[str(team)]


def applied(engine, option):
    s = settings(3)  # Gammas: GAMMA_HURT is in a reserve slot
    with engine.connect() as conn:
        state = load_state(conn, 1, 3)
        rostered = [p.player_id for spots in state.scenario.rosters.values() for p in spots]
        pool = rostered + [fx.STEADY, fx.ROOKIE]
        proj = cache.projections(conn, pool, FMT, s)
        statuses = {pid: st for pid, (_, st) in state.info.items()} | {fx.ROOKIE: "Q"}
        return proj, fragility.apply(option, proj, state.scenario, statuses, conn, s.as_of)


def test_none_is_full_availability_outside_reserve_slots(impact_engine):
    base, out = applied(impact_engine, "none")
    for pid, p in out.items():
        if p.games_found == 0:
            assert p.availability == base[pid].availability  # unprojected stay unprojected
        else:
            assert p.availability == (0.0 if pid == fx.GAMMA_HURT else 1.0)


def test_last15_is_unchanged(impact_engine):
    base, out = applied(impact_engine, "last15")
    assert {p: x.availability for p, x in out.items()} == {
        p: x.availability for p, x in base.items()
    }


def test_dab_tag_scales_only_tagged_players(impact_engine):
    _, dab = applied(impact_engine, "dab")
    _, tag = applied(impact_engine, "dab_tag")
    assert all(0.0 <= p.availability <= 1.0 for p in dab.values())
    for pid in dab:
        mult = {fx.GAMMA_HURT: av.tag_multiplier("IL"), fx.ROOKIE: av.tag_multiplier("Q")}
        want = dab[pid].availability * mult.get(pid, 1.0)
        assert tag[pid].availability == pytest.approx(want)
    assert tag[fx.GAMMA_HURT].availability < dab[fx.GAMMA_HURT].availability


def test_options_change_strategic_results(impact_engine):
    with impact_engine.connect() as conn:
        none = analyze(conn, settings(3, fragility="none"))
        dab = analyze(conn, settings(3, fragility="dab"))
    assert none["settings"]["fragility"] == "none"
    assert none["radar"] != dab["radar"]


def test_default_is_dab_tag(impact_engine):
    assert AnalysisSettings(league_id=1, team_id=1).fragility == "dab_tag"
    client = TestClient(create_app(impact_engine))
    r = client.post(
        "/api/impact/analyze",
        json={"league_id": 1, "team_id": 1, "as_of": "2026-11-18", "iterations": 2000},
    )
    assert r.status_code == 200 and r.json()["settings"]["fragility"] == "dab_tag"


def test_invalid_option_is_422(impact_engine):
    client = TestClient(create_app(impact_engine))
    body = {"league_id": 1, "team_id": 1, "fragility": "sometimes"}
    assert client.post("/api/impact/analyze", json=body).status_code == 422
    assert client.post("/api/impact/players", json=body).status_code == 422
