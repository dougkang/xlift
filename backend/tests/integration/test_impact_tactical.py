"""Tactical = the current matchup: week-to-date totals plus the games left (005 US1)."""

from datetime import date

import pytest
from sqlalchemy import text

from ffmodel.core.scenario import Add, Drop
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

ALPHAS, BETAS, GAMMAS, DELTAS = 1, 2, 3, 4
ZERO = {t: dict.fromkeys(fx.MATCHUP_TOTALS[t], 0) for t in fx.MATCHUP_TOTALS}


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


@pytest.fixture
def matchup(impact_engine):
    def load(**kw):
        cache.clear()
        with impact_engine.begin() as conn:
            fx.load_matchup_state(conn, **kw)

    load()
    return load


def run(engine, moves=(), mode="tactical", team=GAMMAS, **kw):
    with engine.connect() as conn:
        return analyze(
            conn,
            AnalysisSettings(
                league_id=1,
                team_id=team,
                mode=mode,
                as_of=fx.IMPACT_TODAY,
                iterations=10_000,
                **kw,
            ),
            moves,
        )


def codes(result):
    return [w["code"] for w in result["warnings"]]


def test_tactical_shape(impact_engine, matchup):
    r = run(impact_engine)
    rec = r["header"]["record"]
    assert rec["unit"] == "categories" and rec["wins"] + rec["losses"] + rec["ties"] == 9
    assert 0 <= r["header"]["matchup_win_probability"] <= 1
    m = r["header"]["matchup"]
    assert (m["opponent_id"], m["opponent_name"], m["week"]) == (DELTAS, "Deltas", 1)
    assert (m["period_start"], m["period_end"], m["as_of"]) == (
        date(2026, 11, 16),
        date(2026, 11, 22),
        fx.LAST_FINAL,
    )
    assert m["final"] is False
    assert sum(m["current"].values()) == 9
    assert r["settings"]["opponent_id"] == DELTAS
    assert r["matchups"] == [] and r["matchup_totals"] is None  # opponent's roster replaces H2H
    table = r["category_table"]
    assert table["kind"] == "differences"
    for row, cat in zip(table["rows"], r["categories"], strict=True):
        d = row["difference"]
        expected = (
            "even" if d == 0 else "selected" if (d > 0) == cat["higher_is_better"] else "opponent"
        )
        assert row["favors"] == expected, cat["key"]


@pytest.mark.parametrize("team,opponent", [(1, 2), (2, 1), (3, 4), (4, 3)])
def test_opponent_comes_from_the_pairing(impact_engine, matchup, team, opponent):  # SC-001
    r = run(impact_engine, team=team)
    assert r["header"]["matchup"]["opponent_id"] == opponent
    assert [s["emphasis"] for s in r["radar"]["series"]] == ["opponent", "selected"]
    assert all({s["role"] for s in c["series"]} == {"selected", "opponent"} for c in r["curves"])


def test_week_to_date_values(impact_engine, matchup):
    rows = {row["category"]: row for row in run(impact_engine)["category_table"]["rows"]}
    gammas, deltas = fx.MATCHUP_TOTALS[GAMMAS], fx.MATCHUP_TOTALS[DELTAS]
    assert rows["reb"]["selected_actual"] == gammas["reb"]
    assert rows["reb"]["opponent_actual"] == deltas["reb"]
    assert rows["fg_pct"]["selected_actual"] == pytest.approx(gammas["fgm"] / gammas["fga"])


def test_final_total_is_base_plus_remaining(impact_engine, matchup):  # SC-002
    with_base = run(impact_engine)
    matchup(totals=ZERO)
    without = run(impact_engine)
    cats = {c["key"]: c for c in with_base["categories"]}
    for a, b in zip(
        with_base["category_table"]["rows"], without["category_table"]["rows"], strict=True
    ):
        key = a["category"]
        if key in ("fg_pct", "ft_pct"):
            # Ratio of the combined makes and attempts lies between the parts' ratios.
            lo, hi = sorted((a["selected_actual"], b["selected_average"]))
            assert lo - 1e-9 <= a["selected_average"] <= hi + 1e-9, key
            continue
        stat = cats[key]
        assert a["selected_average"] == pytest.approx(
            b["selected_average"] + a["selected_actual"]
        ), stat["label"]
        assert a["opponent_average"] == pytest.approx(
            b["opponent_average"] + a["opponent_actual"]
        ), stat["label"]


def test_remaining_games_start_after_the_as_of_date(impact_engine, matchup):
    def remaining(r, pid):
        gammas = next(t for t in r["rosters"] if t["team_id"] == GAMMAS)
        return {p["player_id"]: p["games_remaining"] for p in gammas["players"]}[pid]

    r = run(impact_engine, [Add(fx.BUSY)])
    assert remaining(r, fx.BUSY) == 4  # BOS: 11-18 … 11-21
    assert remaining(r, fx.GAMMA_1) == 3  # CHI
    assert remaining(r, fx.GAMMA_2) == 1  # MIA: the postponed MIA–NYK game is not counted
    matchup(as_of=date(2026, 11, 18))  # the 11-18 BOS–CHI game is now in the totals
    r = run(impact_engine, [Add(fx.BUSY)])
    assert remaining(r, fx.BUSY) == 3 and remaining(r, fx.GAMMA_1) == 2


def test_remaining_is_by_date_not_status(impact_engine, matchup):
    # Our game data shows the 11-18 game as final, but the capture (as of 11-17) predates it:
    # it is still simulated, and the state is flagged stale.
    with impact_engine.begin() as conn:
        conn.execute(text("UPDATE game SET status = 'final' WHERE game_date = '2026-11-18'"))
    r = run(impact_engine)
    gammas = next(t for t in r["rosters"] if t["team_id"] == GAMMAS)
    assert {p["player_id"]: p["games_remaining"] for p in gammas["players"]}[fx.GAMMA_1] == 3
    assert "MATCHUP_STALE" in codes(r)


def test_final_week(impact_engine, matchup):  # SC-003, FR-011
    matchup(as_of=fx.WEEK[1])
    r = run(impact_engine)
    m = r["header"]["matchup"]
    assert m["final"] is True and "NO_GAMES_REMAINING" in codes(r)
    for row in r["category_table"]["rows"]:
        assert (
            row["win_probability"] in (0.0, 1.0) or row["selected_actual"] == row["opponent_actual"]
        )
    rec = r["header"]["record"]
    assert {k: rec[k] for k in ("wins", "losses", "ties")} == m["current"]
    expected = 1.0 if m["current"]["wins"] > m["current"]["losses"] else 0.0
    assert r["header"]["matchup_win_probability"] == expected


def test_moves_change_only_the_remaining_games(impact_engine, matchup):  # FR-010
    before = run(impact_engine)
    after = run(impact_engine, [Drop(fx.GAMMA_1)])
    assert after["header"]["matchup"]["current"] == before["header"]["matchup"]["current"]
    for a, b in zip(after["category_table"]["rows"], before["category_table"]["rows"], strict=True):
        assert a["selected_actual"] == b["selected_actual"]
    assert [r["selected_average"] for r in after["category_table"]["rows"]] != [
        r["selected_average"] for r in before["category_table"]["rows"]
    ]


def test_streaming_example_on_db(impact_engine, matchup):  # 002 SC-004
    busy = run(impact_engine, [Add(fx.BUSY)])
    steady = run(impact_engine, [Add(fx.STEADY)])
    assert busy["header"]["matchup_win_probability"] >= steady["header"]["matchup_win_probability"]
    reb = {r["category"]: r for r in busy["category_table"]["rows"]}["reb"]
    reb_steady = {r["category"]: r for r in steady["category_table"]["rows"]}["reb"]
    assert reb["selected_average"] > reb_steady["selected_average"]  # more games, more boards


def test_not_loaded(impact_engine):
    r = run(impact_engine)
    assert codes(r) == ["MATCHUP_NOT_LOADED"]
    assert r["header"]["record"] is None and r["radar"] is None and r["curves"] == []
    assert len(r["rosters"]) == 4


def test_roster_and_matchup_dates(impact_engine, matchup):
    assert "ROSTER_MATCHUP_DATES_DIFFER" in codes(run(impact_engine))  # roster 11-18, matchup 11-17
    matchup(as_of=date(2026, 11, 18))
    assert "ROSTER_MATCHUP_DATES_DIFFER" not in codes(run(impact_engine))


def test_modes_compute_differently(impact_engine, matchup):  # Constitution IV
    tactical = run(impact_engine)["category_table"]["rows"]
    strategic = run(impact_engine, mode="strategic")["category_table"]["rows"]
    assert [r["selected_average"] for r in tactical] != [r["average"] for r in strategic]
