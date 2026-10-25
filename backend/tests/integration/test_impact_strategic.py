import json

import pytest
from sqlalchemy import text

from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

ALPHAS, BETAS, GAMMAS, DELTAS = 1, 2, 3, 4


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def run(engine, team=ALPHAS, **kw):
    with engine.connect() as conn:
        return analyze(
            conn, AnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, **kw)
        )


def cat_index(result, key):
    return [c["key"] for c in result["categories"]].index(key)


def test_alphas_record_and_pts_rank(impact_engine):
    r = run(impact_engine)
    rec = r["header"]["record"]
    assert rec["unit"] == "matchups" and rec["wins"] + rec["losses"] + rec["ties"] == 3
    assert r["category_table"]["rows"][cat_index(r, "pts")]["rank"] == 1


def test_radar_and_table(impact_engine):
    r = run(impact_engine)
    series = r["radar"]["series"]
    assert len(series) == 4
    assert [s["emphasis"] for s in series].count("selected") == 1
    assert all(1 <= rank <= 4 for s in series for rank in s["ranks"])
    assert [row["category"] for row in r["category_table"]["rows"]] == [
        c["key"] for c in r["categories"]
    ]


def test_curve_roles(impact_engine):
    alphas, deltas = run(impact_engine), run(impact_engine, team=DELTAS)
    assert len(alphas["curves"]) == 9
    pts = cat_index(alphas, "pts")
    assert {s["role"] for s in alphas["curves"][pts]["series"]} == {
        "selected",
        "next_best",
        "league_average",
    }
    assert {s["role"] for s in deltas["curves"][pts]["series"]} == {
        "selected",
        "leader",
        "league_average",
    }


def test_turnovers_rank_lowest_first(impact_engine):
    results = {t: run(impact_engine, team=t) for t in (ALPHAS, BETAS, GAMMAS, DELTAS)}
    tov = cat_index(results[ALPHAS], "tov")
    averages = {t: r["category_table"]["rows"][tov]["average"] for t, r in results.items()}
    lowest = min(averages, key=averages.get)
    assert results[lowest]["category_table"]["rows"][tov]["rank"] == 1


def test_reserve_player_contributes_nothing(impact_engine):
    before = run(impact_engine, team=GAMMAS)
    with impact_engine.begin() as conn:
        conn.execute(text("DELETE FROM roster_entry WHERE player_id = :p"), {"p": fx.GAMMA_HURT})
    cache.clear()
    after = run(impact_engine, team=GAMMAS)
    assert before["category_table"] == after["category_table"]
    assert before["matchups"] == after["matchups"]


def test_window_changes_projections(impact_engine):
    assert run(impact_engine)["category_table"] != run(impact_engine, window=5)["category_table"]


def test_short_history_footnote(impact_engine):
    assert run(impact_engine, team=DELTAS, window=15)["footnotes"] == []
    with impact_engine.begin() as conn:
        conn.execute(
            text("UPDATE roster_entry SET player_id = :r WHERE player_id = :d"),
            {"r": fx.ROOKIE, "d": fx.DELTA_3},
        )
    r = run(impact_engine, team=DELTAS, window=15)
    assert r["footnotes"] == [{"marker": "*", "player_id": fx.ROOKIE, "text": "* 2 of 15 games"}]
    rookie = next(p for t in r["rosters"] for p in t["players"] if p["player_id"] == fx.ROOKIE)
    assert rookie["footnote_marker"] == "*"


def test_freshness(impact_engine):
    assert run(impact_engine)["freshness"]["nba_data_loaded_at"] == "2026-11-18T08:00:00+00:00"


def test_deterministic(impact_engine):  # SC-002
    a = json.dumps(run(impact_engine), default=str, sort_keys=True)
    cache.clear()
    b = json.dumps(run(impact_engine), default=str, sort_keys=True)
    assert a == b


def test_unsupported_format(impact_engine):
    with impact_engine.begin() as conn:
        conn.execute(text("UPDATE fantasy_league SET scoring_format_id = 'points_unknown'"))
    r = run(impact_engine)
    assert [w["code"] for w in r["warnings"]] == ["UNSUPPORTED_FORMAT"]
    assert r["radar"] is None and r["curves"] == [] and len(r["rosters"]) == 4


def test_table_lists_league_average_and_leader(impact_engine):
    r = run(impact_engine, team=DELTAS)
    pts = r["category_table"]["rows"][cat_index(r, "pts")]
    assert pts["leader_name"] == "Alphas" and pts["leader_average"] > pts["league_average"]
    assert pts["average"] < pts["league_average"]
    fg = r["category_table"]["rows"][cat_index(r, "fg_pct")]
    assert 0 < fg["league_average"] < 1


def test_curve_means_match_table(impact_engine):
    r = run(impact_engine, team=DELTAS)
    i = cat_index(r, "reb")
    row, curve = r["category_table"]["rows"][i], r["curves"][i]
    means = {s["role"]: s["mean"] for s in curve["series"]}
    assert means["selected"] == row["average"]
    assert means["league_average"] == row["league_average"]
    assert means["leader"] == row["leader_average"]


def test_record_table_rows_and_total(impact_engine):
    r = run(impact_engine, team=GAMMAS)
    rows = r["matchups"]
    assert [m["opponent_name"] for m in rows] == ["Alphas", "Betas", "Deltas"]
    for m in rows:
        cr = m["category_record"]
        assert cr["wins"] + cr["losses"] + cr["ties"] == 9
        expected = (
            "win" if m["matchup"]["win"] > 0.5 else "loss" if m["matchup"]["loss"] > 0.5 else "tie"
        )
        assert m["result"] == expected
    totals = r["matchup_totals"]
    rec = r["header"]["record"]
    assert totals["matchups"] == {k: rec[k] for k in ("wins", "losses", "ties")}
    assert totals["categories"]["wins"] == sum(m["category_record"]["wins"] for m in rows)


def test_radar_normalized_averages(impact_engine):
    r = run(impact_engine)
    series = r["radar"]["series"]
    tov = cat_index(r, "tov")
    for i, cat in enumerate(r["categories"]):
        vals = [s["normalized"][i] for s in series]
        assert min(vals) == 0.0 and max(vals) == 1.0, cat["key"]
        best = max(series, key=lambda s: s["normalized"][i])
        assert best["ranks"][i] == 1  # normalized 1 is the rank-1 team
    lowest_tov = min(series, key=lambda s: s["averages"][tov])
    assert lowest_tov["normalized"][tov] == 1.0  # direction applied for TO


def test_radar_win_rates(impact_engine):
    r = run(impact_engine)
    series = r["radar"]["series"]
    for i, cat in enumerate(r["categories"]):
        rates = [s["win_rate"][i] for s in series]
        assert all(0 <= x <= 1 for x in rates)
        assert sum(rates) / len(rates) == pytest.approx(0.5)  # ties count half → mean 0.5
        best = max(series, key=lambda s: s["win_rate"][i])
        assert best["ranks"][i] == 1, cat["key"]


def test_radar_area_scores_relative_to_top_team(impact_engine):
    series = run(impact_engine)["radar"]["series"]
    for scale in ("rank", "average", "win_rate"):
        scores = [s["area"][scale] for s in series]
        assert max(scores) == pytest.approx(1.0) and all(0 <= x <= 1 for x in scores)


def test_ranking_rows_carry_win_rate(impact_engine):
    r = run(impact_engine)
    selected = next(s for s in r["radar"]["series"] if s["emphasis"] == "selected")
    assert [row["win_rate"] for row in r["category_table"]["rows"]] == selected["win_rate"]


def test_radar_league_average_shape(impact_engine):
    """The League Average radar line (strategic), from the server."""
    r = run(impact_engine)
    series = r["radar"]["series"]
    [average] = r["radar"]["league"]
    assert average["role"] == "league_average"
    for i in range(len(r["categories"])):
        assert 0.0 <= average["normalized"][i] <= 1.0
        assert 1 <= average["ranks"][i] <= len(series)
        assert average["win_rate"][i] == pytest.approx(0.5)  # ties count half, so the mean is 0.5
    # A team with the league average would rank behind exactly the teams that beat it.
    row = r["category_table"]["rows"][0]
    better = sum(s["averages"][0] > row["league_average"] for s in series)
    assert average["ranks"][0] == 1 + better


def test_matchup_state_does_not_change_strategic(impact_engine):
    """005 SC-005: strategic results are identical with and without a current matchup."""
    from ffmodel.tools.impact_analysis import cache as impact_cache

    impact_cache.clear()
    before = run(impact_engine)
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn)
    impact_cache.clear()
    after = run(impact_engine)
    before["freshness"].pop("matchup_as_of"), after["freshness"].pop("matchup_as_of")
    assert json.dumps(before, default=str, sort_keys=True) == json.dumps(
        after, default=str, sort_keys=True
    )


def test_footnote_rule_at_the_default_window(impact_engine):
    # 006: the default lookback is 82; every footnote is a player with fewer games than that.
    r = run(impact_engine, team=DELTAS)
    assert r["settings"]["window"] == 82
    rows = {p["player_id"]: p for t in r["rosters"] for p in t["players"]}
    for note in r["footnotes"]:
        found = rows[note["player_id"]]["games_found"]
        assert found < 82 and note["text"] == f"* {found} of 82 games"
