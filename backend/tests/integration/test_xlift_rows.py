"""xLift in the picker and on roster rows (007), on the impact fixture."""

import numpy as np
import pytest

from ffmodel.core.scenario import Add, Drop
from ffmodel.core.scoring import get_format
from ffmodel.core.value import expected_wins, team_keys, weakest
from ffmodel.tools.impact_analysis import cache, fragility, value
from ffmodel.tools.impact_analysis.picker import list_players
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from ffmodel.tools.impact_analysis.state import load_state
from tests.fixtures import impact_dataset as fx

ALPHAS, GAMMAS = 1, 3
FMT = get_format("9cat_h2h")


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()


def settings(team=ALPHAS, **kw):
    return AnalysisSettings(league_id=1, team_id=team, as_of=fx.IMPACT_TODAY, **kw)


def pick(engine, team=ALPHAS, moves=(), **kw):
    s_kw = {k: kw.pop(k) for k in ("fragility", "mode") if k in kw}
    with engine.connect() as conn:
        return list_players(conn, settings(team, **s_kw), moves, **kw)["players"]


def penalizer(conn, s, state):
    """The Fragility Penalty for `s`, as the analysis applies it."""
    statuses = {pid: st for pid, (_, st) in state.info.items()}
    return lambda proj, sc: fragility.apply(s.fragility, proj, sc, statuses, conn, s.as_of)


def wins(engine, s, moves=()):
    """Expected weekly category wins of `s.team_id` in the (moved) scenario, with the cached
    league spread, from the same penalized projections the analysis uses."""
    with engine.connect() as conn:
        state = load_state(conn, s.league_id, s.team_id, moves)
        rostered = [
            p for spots in state.scenario.rosters.values() for p in (x.player_id for x in spots)
        ]
        penalize = penalizer(conn, s, state)
        proj = penalize(cache.projections(conn, rostered, FMT, s), state.scenario)
        spread = value.league_spread(conn, FMT, s, state.snapshot, penalize)
    pl = value.lines(proj, s.games_per_period)
    team_ids, T = value.team_totals(state.scenario, pl, FMT.base_stats)
    return expected_wins(team_ids.index(s.team_id), team_keys(T, FMT), spread), state, pl, T


# --- Picker (US1) -----------------------------------------------------------------------------


def test_every_projected_free_agent_has_xlift(impact_engine):
    rows = pick(impact_engine, free_agents_only=True)
    assert rows and all(isinstance(r["xlift"], float) for r in rows if r["games_found"] > 0)


def test_free_agents_ordered_by_xlift_then_name(impact_engine):
    rows = pick(impact_engine, free_agents_only=True)
    scored = [r for r in rows if r["xlift"] is not None]
    keys = [(-r["xlift"], r["name"]) for r in scored]
    assert keys == sorted(keys)
    assert all(r["xlift"] is None for r in rows[len(scored) :])  # unscored last


def test_pages_concatenate_to_the_full_order(impact_engine):
    full = [r["player_id"] for r in pick(impact_engine, limit=200)]
    paged = [r["player_id"] for r in pick(impact_engine, limit=3, offset=0)] + [
        r["player_id"] for r in pick(impact_engine, limit=200, offset=3)
    ]
    assert paged == full


def test_query_keeps_relative_order(impact_engine):
    full = [r["player_id"] for r in pick(impact_engine, limit=200)]
    hits = [r["player_id"] for r in pick(impact_engine, limit=200, query="streamer")]
    assert len(hits) == 2 and hits == [p for p in full if p in hits]


def test_rostered_players_follow_free_agents_by_xlift(impact_engine):
    rows = pick(impact_engine, limit=200)
    owned = [r["owner_team_id"] is not None for r in rows]
    assert owned == sorted(owned)  # all free agents, then all rostered
    rostered = [r for r in rows if r["owner_team_id"] is not None and r["xlift"] is not None]
    assert [r["xlift"] for r in rostered] == sorted((r["xlift"] for r in rostered), reverse=True)


@pytest.mark.parametrize("option", ["last15", "dab_tag"])
def test_swap_changes_expected_wins_by_listed_xlift(impact_engine, option):
    """SC-007: add the top free agent for the weakest active player."""
    s = settings(fragility=option)
    top = pick(impact_engine, free_agents_only=True, fragility=option)[0]
    before, state, pl, T = wins(impact_engine, s)
    ti = sorted(state.scenario.rosters).index(ALPHAS)
    active = state.scenario.active_players(ALPHAS)
    weak = active[weakest(ti, T, np.array([pl[p] for p in active]), FMT, _spread(impact_engine, s))]
    after, *_ = wins(impact_engine, s, [Drop(weak), Add(top["player_id"])])
    assert after - before == pytest.approx(top["xlift"], abs=0.05)


def _spread(engine, s):
    with engine.connect() as conn:
        state = load_state(conn, 1, s.team_id)
        return value.league_spread(conn, FMT, s, state.snapshot, penalizer(conn, s, state))


# --- Roster rows (US2) ------------------------------------------------------------------------


def run(engine, team=ALPHAS, moves=(), **kw):
    from ffmodel.tools.impact_analysis.analysis import analyze

    with engine.connect() as conn:
        return analyze(conn, settings(team, **kw), moves)


def rows_of(result, team):
    return next(t for t in result["rosters"] if t["team_id"] == team)


def test_full_teams_have_one_zero_weakest(impact_engine):
    r = run(impact_engine, fragility="last15")
    full = [t for t in r["rosters"] if t["open_active_slots"] == 0]
    assert full
    for team in full:
        active = [p["xlift"] for p in team["players"] if p["slot"] == "active"]
        assert all(isinstance(v, float) for v in active)
        assert active.count(0.0) == 1


def test_open_slot_players_score_their_full_contribution(impact_engine):
    s = settings(GAMMAS, fragility="last15")
    r = run(impact_engine, GAMMAS, fragility="last15")
    team = rows_of(r, GAMMAS)
    assert team["open_active_slots"] > 0
    now, state, pl, T = wins(impact_engine, s)
    ti = sorted(state.scenario.rosters).index(GAMMAS)
    spread = _spread(impact_engine, s)
    for p in (p for p in team["players"] if p["slot"] == "active"):
        moved = T.copy()
        moved[ti] = T[ti] - pl[p["player_id"]]
        want = now - expected_wins(ti, team_keys(moved, FMT), spread)
        assert p["xlift"] > 0 and p["xlift"] == pytest.approx(want)


def test_values_follow_moves(impact_engine):
    before = {p["player_id"]: p["xlift"] for p in rows_of(run(impact_engine), ALPHAS)["players"]}
    after = rows_of(run(impact_engine, moves=[Drop(fx.ALPHA_3)]), ALPHAS)
    assert after["open_active_slots"] == 1
    for p in after["players"]:
        assert p["xlift"] > 0 and p["xlift"] != before[p["player_id"]]


def test_reserve_rows_are_scored_as_candidates(impact_engine):
    s = settings(GAMMAS, fragility="last15")
    team = rows_of(run(impact_engine, GAMMAS, fragility="last15"), GAMMAS)
    hurt = next(p for p in team["players"] if p["player_id"] == fx.GAMMA_HURT)
    assert hurt["slot"] == "reserve"
    now, state, pl, T = wins(impact_engine, s)
    ti = sorted(state.scenario.rosters).index(GAMMAS)
    moved = T.copy()
    moved[ti] = T[ti] + pl[fx.GAMMA_HURT]  # Gammas has an open slot: nobody makes room
    want = expected_wins(ti, team_keys(moved, FMT), _spread(impact_engine, s)) - now
    assert hurt["xlift"] == pytest.approx(want)


# --- Tactical opponent (US4) ------------------------------------------------------------------

BETAS = 2  # Alphas' opponent in the fixture's matchup


@pytest.fixture
def matchup(impact_engine):
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn)
    cache.clear()
    return impact_engine


def test_opponent_rows_are_scored_for_the_opponent(matchup):
    r = run(matchup, mode="tactical", iterations=2000)
    assert r["settings"]["opponent_id"] == BETAS
    opp = rows_of(r, BETAS)
    active = [p["xlift"] for p in opp["players"] if p["slot"] == "active"]
    assert opp["open_active_slots"] == 0 and active.count(0.0) == 1
    # The same players scored for the selected team (as acquisitions) give other values.
    for_me = {p["player_id"]: p["xlift"] for p in pick(matchup, mode="tactical", limit=200)}
    assert any(p["xlift"] != for_me[p["player_id"]] for p in opp["players"])


def test_tactical_picker_is_for_the_selected_team(matchup):
    mine = {p["player_id"]: p["xlift"] for p in pick(matchup, ALPHAS, mode="tactical")}
    theirs = {p["player_id"]: p["xlift"] for p in pick(matchup, BETAS, mode="tactical")}
    shared = [pid for pid in mine.keys() & theirs.keys() if mine[pid] is not None]
    assert shared and any(mine[p] != theirs[p] for p in shared)


def test_fragility_changes_only_xlift_in_tactical(matchup):
    """FR-018: tactical odds use games remaining, not availability."""
    none = run(matchup, mode="tactical", iterations=2000, fragility="none")
    dab = run(matchup, mode="tactical", iterations=2000, fragility="dab")
    for key in ("header", "category_table", "curves", "radar"):
        assert none[key] == dab[key]
    xw = lambda r: [p["xlift"] for t in r["rosters"] for p in t["players"]]  # noqa: E731
    assert xw(none) != xw(dab)


def test_active_player_without_games_is_the_baseline(impact_engine):
    """FR-005: an active player with no games is weakest (an empty slot); nobody shows 0."""
    from sqlalchemy import text

    with impact_engine.begin() as conn:
        conn.execute(text("DELETE FROM player_game WHERE player_id = :p"), {"p": fx.ALPHA_3})
    team = rows_of(run(impact_engine, fragility="last15"), ALPHAS)
    assert team["open_active_slots"] == 0
    vals = {p["player_id"]: p["xlift"] for p in team["players"]}
    assert vals[fx.ALPHA_3] is None
    assert all(v > 0 for pid, v in vals.items() if pid != fx.ALPHA_3)
