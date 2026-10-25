"""League-scope xLift (009 research R3): DB-free, on a synthetic 4-team 9cat league."""

from types import MappingProxyType, SimpleNamespace

import numpy as np
import pytest

from ffmodel.core.scenario.scenario import ACTIVE, RosterSpot, Scenario
from ffmodel.core.scoring import get_format
from ffmodel.core.value import score_league_by_category, score_pool_by_category
from tests.unit.test_xlift import SPREAD, line

FMT = get_format("9cat_h2h")
GPP = 3
FREE_AGENTS = (101, 102, 103)


def proj(mean):
    return SimpleNamespace(mean=np.asarray(mean, dtype=float), availability=1.0, games_found=10)


def league(open_slot_team=None):
    """4 teams × 3 actives (capacity 3), free agents 101–103. `open_slot_team` has only 2."""
    rng = np.random.default_rng(11)
    rosters, projections = {}, {}
    pid = 1
    for t in (1, 2, 3, 4):
        spots = []
        for _ in range(2 if t == open_slot_team else 3):
            m = line() * rng.uniform(0.6, 1.4, len(FMT.base_stats)) / GPP
            m[1], m[4] = max(m[1], m[0] + 0.3), max(m[4], m[3] + 0.3)  # attempts > makes
            projections[pid] = proj(m)
            spots.append(RosterSpot(pid, ACTIVE))
            pid += 1
        rosters[t] = tuple(spots)
    for i, fa in enumerate(FREE_AGENTS):
        projections[fa] = proj(line(fgm=9 + i, fga=19, reb=7 + 2 * i, tov=1 + i) / GPP)
    settings = SimpleNamespace(active_roster_capacity=3)
    return Scenario(settings, MappingProxyType(rosters), frozenset()), projections


def score_league(scenario, projections, ids):
    roster = {p: projections[p] for p in scenario.owner}
    pool = {p: projections[p] for p in ids}
    return score_league_by_category(scenario, pool, FMT, GPP, SPREAD, roster)


def per_team(scenario, projections, ids, team):
    roster = {p: projections[p] for p in scenario.owner}
    pool = {p: projections[p] for p in ids}
    return score_pool_by_category(scenario, team, pool, FMT, GPP, SPREAD, roster)


def test_free_agent_is_the_mean_over_every_team():
    sc, pr = league()
    got = score_league(sc, pr, FREE_AGENTS)
    for fa in FREE_AGENTS:
        want = np.mean([per_team(sc, pr, [fa], t)[fa] for t in (1, 2, 3, 4)], axis=0)
        assert np.allclose(got[fa], want, atol=1e-12)


def test_rostered_player_leaves_out_their_own_team():
    sc, pr = league()
    player = sc.rosters[2][0].player_id
    got = score_league(sc, pr, [player])[player]
    want = np.mean([per_team(sc, pr, [player], t)[player] for t in (1, 3, 4)], axis=0)
    assert np.allclose(got, want, atol=1e-12)


def test_each_team_uses_its_own_baseline():
    """A team with an open active slot scores candidates against the empty slot, so its
    per-team values are the full gain; the league mean includes that team's values."""
    sc, pr = league(open_slot_team=3)
    got = score_league(sc, pr, FREE_AGENTS)
    for fa in FREE_AGENTS:
        rows = [per_team(sc, pr, [fa], t)[fa] for t in (1, 2, 3, 4)]
        assert rows[2].sum() > 0  # filling an open slot always adds
        assert np.allclose(got[fa], np.mean(rows, axis=0), atol=1e-12)


def test_rows_sum_to_the_mean_of_per_team_nets():
    sc, pr = league()
    got = score_league(sc, pr, FREE_AGENTS)
    for fa in FREE_AGENTS:
        nets = [per_team(sc, pr, [fa], t)[fa].sum() for t in (1, 2, 3, 4)]
        assert got[fa].sum() == pytest.approx(np.mean(nets), abs=1e-9)


def test_unprojected_player_has_no_value():
    sc, pr = league()
    pr[999] = SimpleNamespace(mean=np.zeros(len(FMT.base_stats)), availability=None, games_found=0)
    assert score_league(sc, pr, [999]) == {999: None}
