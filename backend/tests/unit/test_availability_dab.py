"""dAB in the app (007 research R3): DB-free, on synthetic histories."""

import numpy as np
import pytest

from ffmodel.core.model import availability as av

# Three seasons starting each October.
STARTS = np.array(["2023-10-20", "2024-10-20", "2025-10-20"])


def days(start: str, n: int, step: int = 2) -> np.ndarray:
    d0 = np.datetime64(start)
    return np.array([str(d0 + np.timedelta64(i * step, "D")) for i in range(n)])


def test_age_buckets():
    team = np.concatenate([days("2023-10-20", 20), days("2024-10-20", 20), days("2025-10-20", 20)])
    played = np.concatenate([team[:10], team[20:35], team[40:60]])
    c = av.age_counts(played, team, [], STARTS, "2026-04-01")
    # Window: the last 15 played, all this season; its team games run from the first of them.
    assert c[0].tolist() == [15, 0, 0, 0, 0, 0]
    assert c[1].tolist() == [15, 0, 0, 0, 0, 0]
    # Long run: every game of the last three seasons, by age.
    assert c[2].tolist() == [20, 15, 10, 0, 0, 0]
    assert c[3].tolist() == [20, 20, 20, 0, 0, 0]


def test_short_window_counts_from_first_team_game():
    team = days("2025-10-20", 20)
    played = team[[0, 5, 10]]
    c = av.age_counts(played, team, [], STARTS, "2026-04-01")
    assert c[0, 0] == 3 and c[1, 0] == 20


def test_missed_season_counts_only_after_return():
    team = np.concatenate([days("2023-10-20", 10), days("2025-10-20", 10)])
    played = team.copy()
    gap = (days("2024-10-20", 8, step=20), "2025-10-20")
    before = av.age_counts(played[:10], team[:10], [gap], STARTS, "2025-01-01")
    after = av.age_counts(played, team, [gap], STARTS, "2026-04-01")
    assert before[3].sum() == 10  # the gap isn't known yet
    assert after[3].tolist() == [10, 8, 10, 0, 0, 0]
    assert after[2].tolist() == [10, 0, 10, 0, 0, 0]


def test_blend_formula():
    c = np.zeros((4, av.AGES))
    c[:, 0] = [9, 15, 40, 60]
    c[:, 1] = [0, 0, 50, 70]
    w = av.DELTA ** np.arange(av.AGES)
    wp, wt, lp, lt = c @ w
    win = (wp + av.KAPPA_W * av.ABAR) / (wt + av.KAPPA_W)
    long = (lp + av.KAPPA * av.ABAR) / (lt + av.KAPPA)
    want = av.ABAR + av.B1 * (win - av.ABAR) + av.B2 * (long - av.ABAR)
    assert av.dab(c) == pytest.approx(want)


def test_clipped_to_unit_interval():
    c = np.zeros((4, av.AGES))
    c[:, 0] = [15, 15, 100, 100]
    assert 0.0 <= av.dab(c) <= 1.0
    c[:, 0] = [0, 15, 0, 100]
    assert 0.0 <= av.dab(c) <= 1.0


def test_no_evidence_gives_league_rate():
    assert av.dab(None) == av.ABAR
    assert av.age_counts(av._EMPTY, days("2025-10-20", 5), [], STARTS, "2026-04-01") is None


def test_tag_multipliers():
    assert av.tag_multiplier("IL") == 0.3
    assert av.tag_multiplier("O") == 0.6
    assert av.tag_multiplier("Q") == 0.9
    assert av.tag_multiplier("healthy") == 1.0
    assert av.tag_multiplier(None) == 1.0
