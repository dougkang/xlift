"""Week-to-date base totals in the simulation (005 research R3)."""

import numpy as np

from ffmodel.core.sim import TACTICAL, category_values, simulate_team, tactical_k
from tests.sim_helpers import FMT, projection

IT = 5_000
# fgm, fga, fg3m, ftm, fta, reb, ast, stl, blk, tov
BASE = np.array([40, 80, 10, 20, 25, 60, 30, 8, 6, 12], dtype=float)


def sim(projs, base=None, seed=11):
    return simulate_team(
        1, projs, tactical_k, FMT, iterations=IT, seed=seed, mode_code=TACTICAL, base=base
    )


def test_base_order_matches_format():
    assert FMT.base_stats == ("fgm", "fga", "fg3m", "ftm", "fta", "reb", "ast", "stl", "blk", "tov")


def test_no_base_is_unchanged():
    projs = [projection(i, games_remaining=3) for i in (1, 2)]
    a, b = sim(projs), sim(projs, base=None)
    for stat in a.totals:
        np.testing.assert_array_equal(a.totals[stat], b.totals[stat])


def test_base_is_added_after_the_remainder_is_made_valid():
    # Tiny means with large spread: the raw remainder is often negative and gets clipped.
    projs = [projection(i, scale=0.05, sd_frac=3.0, games_remaining=2) for i in (1, 2)]
    plain, based = sim(projs), sim(projs, base=BASE)
    for i, stat in enumerate(FMT.base_stats):
        np.testing.assert_array_equal(based.totals[stat], plain.totals[stat] + BASE[i])
        assert (based.totals[stat] >= BASE[i]).all()  # clipping never eats real totals
    t = based.totals
    assert (t["fgm"] <= t["fga"]).all() and (t["fg3m"] <= t["fgm"]).all()
    assert (t["ftm"] <= t["fta"]).all()
    assert (t["pts"] == 2 * t["fgm"] + t["fg3m"] + t["ftm"]).all()  # derived from the sum


def test_no_games_remaining_equals_the_base():
    projs = [projection(i, games_remaining=0) for i in (1, 2)]
    t = sim(projs, base=BASE).totals
    for i, stat in enumerate(FMT.base_stats):
        assert (t[stat] == BASE[i]).all()
    keys = [c.key for c in FMT.categories]
    v = category_values(sim(projs, base=BASE), FMT)
    assert np.allclose(v[:, keys.index("fg_pct")], 40 / 80)  # makes ÷ attempts of the base
