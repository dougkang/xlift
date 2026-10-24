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
