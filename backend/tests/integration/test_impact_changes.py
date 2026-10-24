"""003: before/after `changes` block on the impact fixture."""

import numpy as np
import pytest

from ffmodel.core.scenario import Add, Drop, Swap
from ffmodel.tools.impact_analysis import analysis, cache
from ffmodel.tools.impact_analysis.changes import transition
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

ALPHAS, BETAS, GAMMAS, DELTAS = 1, 2, 3, 4
IT = 4000


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def settings(team=DELTAS, **kw):
    return AnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, iterations=IT, **kw)


def run(engine, moves=(), **kw):
    with engine.connect() as conn:
        return analysis.analyze(conn, settings(**kw), moves)


TRADE = [Swap(acquire_id=fx.ALPHA_1, give_id=fx.DELTA_1, team_id=DELTAS)]


def test_no_moves_no_changes(impact_engine):
    assert run(impact_engine)["changes"] is None


def test_headline_strategic(impact_engine):
    before, after = run(impact_engine), run(impact_engine, TRADE)
    ch = after["changes"]["header"]
    b, a = before["header"]["record"], after["header"]["record"]
    for k, better_when in (("wins", "higher"), ("losses", "lower")):
        d = a[k] - b[k]
        if d == 0:
            assert ch[k] is None
        else:
            assert ch[k]["delta"] == d
            assert ch[k]["tone"] == ("better" if (d > 0) == (better_when == "higher") else "worse")
    assert ch["chance_to_win"] is None


def test_headline_tactical(impact_engine):
    kw = {"team": GAMMAS, "mode": "tactical", "opponent_id": DELTAS}
    moves = [Swap(acquire_id=fx.DELTA_1, give_id=fx.GAMMA_2, team_id=GAMMAS)]
    before, after = run(impact_engine, **kw), run(impact_engine, moves, **kw)
    expected = round(
        (after["header"]["matchup_win_probability"] - before["header"]["matchup_win_probability"])
        * 100
    )
    ch = after["changes"]
    assert ch["header"]["chance_to_win"]["delta"] == expected
    assert ch["header"]["wins"] is None
    # Trade with the opponent: both originals drawn, opponent averages inverted.
    assert {o["team_id"] for o in ch["radar"]["original"]} == {GAMMAS, DELTAS}
    roles = {s["role"] for s in after["curves"][0]["series"]}
    assert "selected_original" in roles and "opponent_original" not in roles
    pts = ch["category_table"]["pts"]["opponent_average"]
    assert pts is not None and pts["tone"] == ("better" if pts["delta"] < 0 else "worse")


def test_free_agent_add_leaves_untouched_teams_identical(impact_engine):  # SC-003
    with impact_engine.connect() as conn:
        s = settings(team=GAMMAS)
        _, orig = cache.original(
            conn, analysis.normalize(s), lambda: analysis._analyze(conn, analysis.normalize(s), ())
        )
        result, comp = analysis._analyze(
            conn, analysis.normalize(s), [Add(fx.BUSY, GAMMAS)], reuse=orig
        )
    for tid in (ALPHAS, BETAS, DELTAS):
        assert comp.samples[tid] is orig.samples[tid]
        np.testing.assert_array_equal(comp.values[tid], orig.values[tid])
    assert comp.samples[GAMMAS] is not orig.samples[GAMMAS]


def test_category_table_and_tones(impact_engine):
    before, after = run(impact_engine), run(impact_engine, TRADE)
    rows_b = {r["category"]: r for r in before["category_table"]["rows"]}
    for cat, row in zip(after["categories"], after["category_table"]["rows"], strict=True):
        ch = after["changes"]["category_table"][cat["key"]]
        d_rank = row["rank"] - rows_b[cat["key"]]["rank"]
        assert (ch["rank"] or {}).get("delta", 0) == d_rank
        if ch["rank"]:
            assert ch["rank"]["tone"] == ("better" if d_rank < 0 else "worse")
        if ch["average"]:
            up = ch["average"]["delta"] > 0
            assert ch["average"]["tone"] == ("better" if up == cat["higher_is_better"] else "worse")
        for neutral in ("league_average", "leader_average"):
            assert ch[neutral] is None or ch[neutral]["tone"] == "neutral"


def test_radar_changes(impact_engine):
    after = run(impact_engine, TRADE)
    radar = after["changes"]["radar"]
    assert [o["team_id"] for o in radar["original"]] == [DELTAS]
    cur = next(s for s in after["radar"]["series"] if s["team_id"] == DELTAS)
    orig = radar["original"][0]
    tones = radar["tones"][str(DELTAS)]
    for i, tone in enumerate(tones["rank"]):
        d = cur["ranks"][i] - orig["ranks"][i]
        assert tone == (None if d == 0 else "better" if d < 0 else "worse")
    for scale, field in (("average", "normalized"), ("win_rate", "win_rate")):
        assert len(tones[scale]) == 9
        for i, tone in enumerate(tones[scale]):
            if tone:
                assert (cur[field][i] > orig[field][i]) == (tone == "better")
    assert set(radar["area"]) == {"rank", "average", "win_rate"}


def test_curves_have_originals_and_mean_changes(impact_engine):
    before, after = run(impact_engine), run(impact_engine, TRADE)
    for cat, curve, curve_b in zip(
        after["categories"], after["curves"], before["curves"], strict=True
    ):
        roles = {s["role"]: s for s in curve["series"]}
        assert len(roles["selected_original"]["density"]) == len(curve["x"])
        mean_b = next(s["mean"] for s in curve_b["series"] if s["role"] == "selected")
        ch = after["changes"]["curves"][cat["key"]]["means"]["selected"]
        decimals = 3 if cat["decimals"] else 1
        expected = round(roles["selected"]["mean"] - mean_b, decimals)
        assert (ch["delta"] if ch else 0) == expected


def test_transitions_match_results(impact_engine):
    before, after = run(impact_engine), run(impact_engine, TRADE)
    res_b = {m["opponent_id"]: m["result"] for m in before["matchups"]}
    flips = 0
    for m in after["matchups"]:
        ch = after["changes"]["matchups"][str(m["opponent_id"])]
        assert ch["original_result"] == res_b[m["opponent_id"]]
        assert ch["transition"] == transition(res_b[m["opponent_id"]], m["result"])
        flips += ch["transition"] == "flip_better"
    assert flips >= 1  # the fixture trade flips at least one L to W
    totals = after["changes"]["matchup_totals"]
    assert set(totals) == {"matchups", "categories"}


def test_original_cache_hit(impact_engine, monkeypatch):
    calls = {"n": 0}
    real = analysis._analyze

    def counting(conn, s, moves, reuse=None):
        if not moves:
            calls["n"] += 1
        return real(conn, s, moves, reuse=reuse)

    monkeypatch.setattr(analysis, "_analyze", counting)
    run(impact_engine, [Drop(fx.DELTA_1, DELTAS)])
    run(impact_engine, [Drop(fx.DELTA_2, DELTAS)])
    assert calls["n"] == 1


def test_settings_change_recomputes_original(impact_engine):  # US3
    moves = [Drop(fx.DELTA_1, DELTAS)]
    after10 = run(impact_engine, moves, window=10)
    base10, cur10 = run(impact_engine, window=10), run(impact_engine, moves, window=10)
    rec_b, rec_c = base10["header"]["record"], cur10["header"]["record"]
    wins = after10["changes"]["header"]["wins"]
    assert (wins["delta"] if wins else 0) == rec_c["wins"] - rec_b["wins"]
    # Another selected team compares its own original roster.
    other = run(impact_engine, [Drop(fx.GAMMA_1, GAMMAS)], team=GAMMAS)
    assert [o["team_id"] for o in other["changes"]["radar"]["original"]] == [GAMMAS]


def test_opponent_switch_recomputes_original(impact_engine):
    moves = [Add(fx.BUSY, GAMMAS)]
    a = run(impact_engine, moves, team=GAMMAS, mode="tactical", opponent_id=BETAS)
    b = run(impact_engine, moves, team=GAMMAS, mode="tactical", opponent_id=DELTAS)
    base_b = run(impact_engine, team=GAMMAS, mode="tactical", opponent_id=DELTAS)
    expected = round(
        (b["header"]["matchup_win_probability"] - base_b["header"]["matchup_win_probability"]) * 100
    )
    got = b["changes"]["header"]["chance_to_win"]
    assert (got["delta"] if got else 0) == expected
    assert a["settings"]["opponent_id"] == BETAS
