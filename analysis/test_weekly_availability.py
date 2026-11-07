"""Synthetic check of the weekly dAB backtest: a player who sat out last week is caught."""

import availability as av
import numpy as np
import weekly_availability as wa


def _season_days(start, n):
    return np.array([str(np.datetime64(start) + np.timedelta64(2 * i, "D")) for i in range(n)])


def _data(rng):
    seasons, team, played, mins = [], {}, {}, {}
    starts = ["2022-10-18", "2023-10-24", "2024-10-22"]
    days = [_season_days(s, 82) for s in starts]
    for i, (s, d) in enumerate(zip(starts, days)):
        seasons.append((f"S{i}", d[0], d[-1], 1230))
    for pid in range(40):
        t = np.concatenate(days)
        # Injury spells: a run of misses, so last week predicts next week.
        miss = np.zeros(len(t), bool)
        for start in rng.choice(len(t), 4, replace=False):
            miss[start : start + rng.integers(3, 12)] = True
        miss |= rng.random(len(t)) < 0.05
        p = t[~miss]
        team[pid], played[pid], mins[pid] = t, p, np.full(len(p), 30.0)
    return av.AvailabilityData(seasons, played, mins, team)


def test_recent_terms_help_on_spells():
    obs = wa.build(_data(np.random.default_rng(0)))
    assert len(obs.season) > 100
    assert obs.counts.shape[1:] == (4, av.AGES)
    res = wa.run(obs)["week"]["scores"]
    assert res["+ last week"]["all"]["MSE"] < res["refit"]["all"]["MSE"]
    assert res["+ out"]["out last week"]["bias"] > res["zero rule"]["out last week"]["bias"] - 1


def test_terms():
    obs = wa.build(_data(np.random.default_rng(1)))
    out = wa.out_flag(obs) > 0
    assert np.all(obs.week_p[out] == 0)
    r = wa.recent_term(obs, 2, 0.0)
    assert np.all((r >= 0) & (r <= 1))
    md = wa.report(wa.run(obs), obs)
    assert "Target: week" in md and "Target: 15 games" in md
