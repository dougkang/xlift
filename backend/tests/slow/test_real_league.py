"""SC-001 (speed) and SC-003 (seed stability) on the real league. Manual: uv run pytest -m slow

Uses the database at FFMODEL_DB_URL (default data/ffmodel.sqlite) and league `ccsv-2026`.
"""

import time

import numpy as np
import pytest
from sqlalchemy import text

from ffmodel.contract.db import get_engine
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings

pytestmark = pytest.mark.slow
LEAGUE_KEY = "ccsv-2026"


@pytest.fixture(scope="module")
def league():
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT league_id FROM fantasy_league WHERE league_key = :k"), {"k": LEAGUE_KEY}
        ).first()
        if row is None:
            pytest.skip(f"league {LEAGUE_KEY} not loaded")
        teams = [
            t
            for (t,) in conn.execute(
                text(
                    "SELECT fantasy_team_id FROM fantasy_team WHERE league_id = :l"
                    " ORDER BY source_team_key"
                ),
                {"l": row[0]},
            )
        ]
    return engine, row[0], teams


def settings(league_id, team, mode, teams, seed=20261023):
    opponent = next(t for t in teams if t != team) if mode == "tactical" else None
    return AnalysisSettings(
        league_id=league_id, team_id=team, mode=mode, opponent_id=opponent, seed=seed
    )


def timed(conn, s):
    start = time.perf_counter()
    result = analyze(conn, s)
    return result, time.perf_counter() - start


def test_sc001_under_two_seconds(league):
    engine, league_id, teams = league
    with engine.connect() as conn:
        cache.clear()
        _, cold = timed(conn, settings(league_id, teams[0], "strategic", teams))
        assert cold < 2.0, f"cold {cold:.2f}s"
        worst = 0.0
        for mode in ("strategic", "tactical"):
            for team in teams[:3]:
                _, warm = timed(conn, settings(league_id, team, mode, teams))
                worst = max(worst, warm)
        print(f"\nSC-001: cold {cold:.2f}s, worst warm {worst:.2f}s")
        assert worst < 2.0


def probabilities(result) -> np.ndarray:
    out = []
    for m in result["matchups"]:
        out.append(m["matchup"]["win"])
        out.extend(c["win"] for c in m["categories"].values())
    return np.array(out)


def test_sc003_seed_stability(league):
    engine, league_id, teams = league
    worst = 0.0
    with engine.connect() as conn:
        for mode in ("strategic", "tactical"):
            for team in teams:
                runs = [
                    probabilities(analyze(conn, settings(league_id, team, mode, teams, seed)))
                    for seed in range(1, 6)
                ]
                spread = np.max(runs, axis=0) - np.min(runs, axis=0)
                worst = max(worst, float(spread.max()))
    print(f"\nSC-003: max spread across 5 seeds = {worst * 100:.2f} percentage points")
    assert worst <= 0.03


def test_sc001_with_moves(league):  # 003 SC-001
    from ffmodel.core.data import get_free_agents, get_league
    from ffmodel.core.scenario import Add, Drop

    engine, league_id, teams = league
    worst = {}
    with engine.connect() as conn:
        snap = get_league(conn, league_id)
        free_agent = get_free_agents(conn, league_id)[0].player_id
        for mode in ("strategic", "tactical"):
            team = teams[0]
            roster = next(t for t in snap.teams if t.fantasy_team_id == team).roster
            drop = next(r.player.player_id for r in roster if r.slot == "active")
            moves = [Drop(drop, team), Add(free_agent, team)]
            cache.clear()
            s = settings(league_id, team, mode, teams)
            start = time.perf_counter()
            analyze(conn, s, moves)
            cold = time.perf_counter() - start
            start = time.perf_counter()
            result = analyze(conn, s, moves[:1])
            warm = time.perf_counter() - start
            assert result["changes"] is not None
            worst[mode] = (round(cold, 2), round(warm, 2))
            assert cold < 2.0 and warm < 2.0
    print(f"\n003 SC-001 with moves (cold, warm): {worst}")
