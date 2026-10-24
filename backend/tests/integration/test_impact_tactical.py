from datetime import date

import pytest

from ffmodel.core.scenario import Add
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

ALPHAS, BETAS, GAMMAS, DELTAS = 1, 2, 3, 4


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def run(engine, moves=(), mode="tactical", opponent=BETAS, **kw):
    with engine.connect() as conn:
        return analyze(
            conn,
            AnalysisSettings(
                league_id=1,
                team_id=GAMMAS,
                mode=mode,
                opponent_id=opponent,
                as_of=fx.IMPACT_TODAY,
                iterations=10_000,
                **kw,
            ),
            moves,
        )


def test_tactical_shape(impact_engine):
    r = run(impact_engine)
    rec = r["header"]["record"]
    assert rec["unit"] == "categories" and rec["wins"] + rec["losses"] + rec["ties"] == 9
    assert 0 <= r["header"]["matchup_win_probability"] <= 1
    assert r["settings"]["period_start"] == date(2026, 11, 16)
    assert r["settings"]["period_end"] == date(2026, 11, 22)
    table = r["category_table"]
    assert table["kind"] == "differences"
    for row, cat in zip(table["rows"], r["categories"], strict=True):
        d = row["difference"]
        expected = (
            "even" if d == 0 else "selected" if (d > 0) == cat["higher_is_better"] else "opponent"
        )
        assert row["favors"] == expected, cat["key"]
    betas = next(m for m in r["matchups"] if m["opponent_id"] == BETAS)
    for row in table["rows"]:
        assert row["win_probability"] == betas["categories"][row["category"]]["win"]


def test_overlays_are_opponent_only(impact_engine):
    r = run(impact_engine)
    assert [s["emphasis"] for s in r["radar"]["series"]] == ["opponent", "selected"]
    assert all({s["role"] for s in c["series"]} == {"selected", "opponent"} for c in r["curves"])
    # H2H is league-wide in tactical mode too; the chosen opponent's row matches the headline.
    assert [m["opponent_name"] for m in r["matchups"]] == ["Alphas", "Betas", "Deltas"]
    betas = next(m for m in r["matchups"] if m["opponent_id"] == BETAS)
    assert betas["matchup"]["win"] == r["header"]["matchup_win_probability"]
    rec = r["header"]["record"]
    assert betas["category_record"] == {k: rec[k] for k in ("wins", "losses", "ties")}


def test_games_remaining_on_rosters(impact_engine):
    r = run(impact_engine, [Add(fx.BUSY)])
    gammas = next(t for t in r["rosters"] if t["team_id"] == GAMMAS)
    remaining = {p["player_id"]: p["games_remaining"] for p in gammas["players"]}
    assert remaining[fx.BUSY] == 4  # BOS
    assert remaining[fx.GAMMA_1] == 3  # CHI
    assert remaining[fx.GAMMA_2] == 1  # MIA: the postponed MIA–NYK game is not counted


def expected_wins(result):
    return sum(m["matchup"]["win"] for m in result["matchups"])


def test_streaming_example_on_db(impact_engine):  # SC-004
    busy = run(impact_engine, [Add(fx.BUSY)])
    steady = run(impact_engine, [Add(fx.STEADY)])
    assert busy["header"]["matchup_win_probability"] > steady["header"]["matchup_win_probability"]
    busy_s = run(impact_engine, [Add(fx.BUSY)], mode="strategic", opponent=None)
    steady_s = run(impact_engine, [Add(fx.STEADY)], mode="strategic", opponent=None)
    assert expected_wins(steady_s) > expected_wins(busy_s)


def test_opponent_required(impact_engine):
    r = run(impact_engine, opponent=None)
    assert [w["code"] for w in r["warnings"]] == ["OPPONENT_REQUIRED"]
    assert r["header"]["record"] is None and r["radar"] is None and r["curves"] == []
    assert len(r["rosters"]) == 4


def test_no_games_remaining(impact_engine):
    r = run(impact_engine, period_start=date(2026, 11, 23), period_end=date(2026, 11, 23))
    assert "NO_GAMES_REMAINING" in [w["code"] for w in r["warnings"]]


def test_modes_compute_differently(impact_engine):  # Constitution IV
    tactical = run(impact_engine)["category_table"]["rows"]
    strategic = run(impact_engine, mode="strategic", opponent=None)["category_table"]["rows"]
    assert [r["selected_average"] for r in tactical] != [r["average"] for r in strategic]
