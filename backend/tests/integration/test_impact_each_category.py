"""H2H each-category standings (010): the expected category record, in both modes."""

import pytest
from sqlalchemy import text

from ffmodel.api.schemas import AnalysisResult
from ffmodel.core.scenario import Add, Drop
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

GAMMAS = 3
N_CATS = 9


@pytest.fixture
def each(impact_engine):
    with impact_engine.begin() as conn:
        conn.execute(text("UPDATE fantasy_league SET scoring_format_id = '9cat_h2h_each'"))
        fx.load_matchup_state(conn, as_of=fx.IMPACT_TODAY)
    cache.clear()
    return impact_engine


def run(engine, moves=(), mode="strategic", team=GAMMAS):
    with engine.connect() as conn:
        r = analyze(
            conn,
            AnalysisSettings(
                league_id=1, team_id=team, mode=mode, as_of=fx.IMPACT_TODAY, iterations=2000
            ),
            moves,
        )
    AnalysisResult.model_validate(r)  # the API contract accepts it
    return r


def total(rec):
    return rec["wins"] + rec["losses"] + rec["ties"]


def test_strategic_headline_is_the_expected_category_record(each):  # FR-007, SC-001, SC-002
    r = run(each)
    assert r["standings"] == "category"
    assert r["header"]["record"] is None
    rec = r["header"]["expected_record"]
    opponents = len(r["matchups"])
    assert total(rec) == pytest.approx(N_CATS * opponents)
    assert rec["win_pct"] == pytest.approx((rec["wins"] + 0.5 * rec["ties"]) / total(rec))
    # The standings win % is the selected team's mean radar Win %: the same odds.
    mine = next(s for s in r["radar"]["series"] if s["team_id"] == GAMMAS)
    assert rec["win_pct"] == pytest.approx(sum(mine["win_rate"]) / N_CATS, abs=1e-9)


def test_h2h_rows_and_total(each):  # FR-012, FR-013, SC-005
    r = run(each)
    for row in r["matchups"]:
        assert row["result"] is None
        assert total(row["expected_record"]) == pytest.approx(N_CATS)
        cats = row["categories"].values()
        assert row["expected_record"]["ties"] == pytest.approx(sum(c["tie"] for c in cats))
    totals = r["matchup_totals"]
    assert totals["matchups"] is None
    assert totals["expected"] == pytest.approx(r["header"]["expected_record"])


def test_tactical_headline_is_this_weeks_expected_record(each):  # FR-009
    r = run(each, mode="tactical")
    assert r["header"]["record"] is None
    rec = r["header"]["expected_record"]
    assert total(rec) == pytest.approx(N_CATS)
    odds = [row["win_probability"] for row in r["category_table"]["rows"]]
    assert rec["wins"] == pytest.approx(sum(odds))
    assert r["header"]["matchup"]["current"]  # the score so far is unchanged (FR-011)


def test_final_week_expected_record_is_the_final_score(each):  # US3 AS2
    with each.begin() as conn:
        fx.load_matchup_state(conn, as_of=fx.WEEK[1])
    cache.clear()
    r = run(each, mode="tactical")
    rec, now = r["header"]["expected_record"], r["header"]["matchup"]["current"]
    assert {k: rec[k] for k in ("wins", "losses", "ties")} == pytest.approx(now)


@pytest.mark.parametrize("mode", ["strategic", "tactical"])
def test_move_changes_expected_wins(each, mode):  # FR-015, FR-016, SC-003
    base = run(each, mode=mode)
    r = run(each, [Drop(fx.GAMMA_1), Add(fx.BUSY)], mode=mode)
    ch = r["changes"]
    delta = r["header"]["expected_record"]["wins"] - base["header"]["expected_record"]["wins"]
    assert abs(delta) >= 0.1
    head = ch["header"]
    assert head["expected_wins"]["delta"] == pytest.approx(round(delta, 1))
    assert head["expected_wins"]["tone"] == ("better" if delta > 0 else "worse")
    assert head["wins"] is None and head["chance_to_win"] is None
    assert (head["win_pct"] is None) == (mode == "tactical")
    for row in ch["matchups"].values():
        assert row["transition"] is None and row["original_result"] is None
    if mode == "strategic":
        assert ch["matchup_totals"]["matchups"] is None
        assert ch["matchup_totals"]["expected_wins"] == head["expected_wins"]


def test_most_categories_unaffected(impact_engine):  # FR-008, FR-020
    with impact_engine.connect() as conn:
        r = analyze(conn, AnalysisSettings(league_id=1, team_id=GAMMAS, as_of=fx.IMPACT_TODAY))
    assert r["standings"] == "matchup"
    assert r["header"]["record"]["unit"] == "matchups"
    assert r["header"]["expected_record"] is None
    assert all(m["result"] in ("win", "loss", "tie") for m in r["matchups"])
