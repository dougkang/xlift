import numpy as np
import pytest

from ffmodel.core.sim import (
    STRATEGIC,
    TACTICAL,
    Odds,
    Record,
    category_values,
    matchup_odds,
    projected_averages,
    ranks,
    record,
    simulate_team,
    strategic_k,
    tactical_k,
)
from tests.sim_helpers import FMT, projection

IT = 10_000


def sim(team_id, projs, k=None, seed=7, mode=STRATEGIC, iterations=IT):
    return simulate_team(
        team_id, projs, k or strategic_k(3), FMT, iterations=iterations, seed=seed, mode_code=mode
    )


def test_ratio_categories_equal_team_makes_over_attempts():  # SC-006
    ts = sim(1, [projection(i) for i in range(1, 4)])
    v = category_values(ts, FMT)
    keys = [c.key for c in FMT.categories]
    t = ts.totals
    with np.errstate(invalid="ignore", divide="ignore"):
        np.testing.assert_array_equal(v[:, keys.index("fg_pct")], t["fgm"] / t["fga"])
        np.testing.assert_array_equal(v[:, keys.index("ft_pct")], t["ftm"] / t["fta"])
    assert (t["fgm"] <= t["fga"]).all() and (t["fg3m"] <= t["fgm"]).all()
    assert (t["ftm"] <= t["fta"]).all()
    assert (t["pts"] == 2 * t["fgm"] + t["fg3m"] + t["ftm"]).all()


def test_zero_attempts_is_nan():
    zero = projection(1, means={s: 0.0 for s in FMT.base_stats}, sd_frac=0)
    v = category_values(sim(1, [zero]), FMT)
    keys = [c.key for c in FMT.categories]
    assert np.isnan(v[:, keys.index("fg_pct")]).all()


def test_dominant_team_wins_everything():  # SC-005
    better = {
        "fgm": 9,
        "fga": 15,
        "fg3m": 2,
        "ftm": 4.7,
        "fta": 5,
        "reb": 6,
        "ast": 5,
        "stl": 1,
        "blk": 1,
        "tov": 2,
    }  # better shooting %, not just more volume
    teams = {1: [projection(10 + i, 1.3, tov_scale=0.7, means=better) for i in range(3)]}
    for t in (2, 3, 4):
        teams[t] = [projection(10 * t + i, 1.0) for i in range(3)]
    samples = {t: sim(t, p) for t, p in teams.items()}
    values = {t: category_values(s, FMT) for t, s in samples.items()}
    odds = [matchup_odds(1, values[1], o, values[o], FMT).matchup for o in (2, 3, 4)]
    assert record(odds) == Record(3, 0, 0)
    r = ranks({t: projected_averages(s, FMT) for t, s in samples.items()}, FMT)
    assert r[1] == [1] * len(FMT.categories)


def test_identical_teams_tie():
    a = sim(1, [projection(5)])
    b = sim(2, [projection(5)])
    o = matchup_odds(1, category_values(a, FMT), 2, category_values(b, FMT), FMT)
    assert all(c.tie == 1.0 for c in o.categories) and o.matchup.tie == 1.0


def test_deterministic_and_seed_sensitive():  # SC-002
    p = [projection(i) for i in range(1, 4)]
    a, b, c = sim(1, p, seed=1), sim(1, p, seed=1), sim(1, p, seed=2)
    for s in a.totals:
        np.testing.assert_array_equal(a.totals[s], b.totals[s])
    assert any(not np.array_equal(a.totals[s], c.totals[s]) for s in a.totals)


def test_common_random_numbers():
    team_b = [projection(20), projection(21)]
    before = sim(2, team_b)
    sim(1, [projection(10), projection(11)])
    sim(1, [projection(10), projection(12)])  # a move on team A
    after = sim(2, team_b)
    for s in before.totals:
        np.testing.assert_array_equal(before.totals[s], after.totals[s])


def test_no_clipping_bias():
    low = {s: 0.0 for s in FMT.base_stats} | {"blk": 0.3, "fga": 1.0}
    team = [projection(i, means=low, sd_frac=0) for i in range(10)]
    team = [
        type(p)(
            p.player_id,
            15,
            15,
            p.mean,
            np.diag(np.where(p.mean > 0, 0.55, 1e-3)),
            p.mean_stderr,
            availability=1.0,
        )
        for p in team
    ]
    ts = sim(1, team, k=strategic_k(3), iterations=50_000)
    assert ts.totals["blk"].mean() == pytest.approx(9.0, rel=0.01)


def test_strategic_k_uses_availability():
    p = projection(1, availability=0.5)
    k = strategic_k(3)(p, np.random.default_rng(0), 100_000)
    assert k.mean() == pytest.approx(1.5, rel=0.02)
    assert tactical_k(projection(1, games_remaining=4), np.random.default_rng(0), 3).tolist() == [
        4.0,
        4.0,
        4.0,
    ]


def test_competition_ranking_and_direction():
    n = len(FMT.categories)
    avgs = {t: np.full(n, v) for t, v in zip((1, 2, 3, 4), (10.0, 8.0, 8.0, 5.0), strict=True)}
    r = ranks(avgs, FMT)
    tov = [c.key for c in FMT.categories].index("tov")
    assert [r[t][0] for t in (1, 2, 3, 4)] == [1, 2, 2, 4]
    assert [r[t][tov] for t in (1, 2, 3, 4)] == [4, 2, 2, 1]


def test_record_rule_half_is_tie():
    assert record([Odds(0.5, 0.0, 0.5), Odds(0.51, 0, 0.49), Odds(0.2, 0.1, 0.7)]) == Record(
        1, 1, 1
    )


def test_tactical_mode_code_changes_stream():
    p = [projection(1, games_remaining=3)]
    a = sim(1, p, k=tactical_k, mode=TACTICAL)
    b = sim(1, p, k=tactical_k, mode=STRATEGIC)
    assert not np.array_equal(a.totals["reb"], b.totals["reb"])
