"""xLift broken down by category (009 research R2): DB-free, on a synthetic 4-team 9cat league."""

import numpy as np

from ffmodel.core.scoring import get_format
from ffmodel.core.value import score_candidates, score_candidates_by_category, weakest
from tests.unit.test_xlift import SPREAD, STATS, league, line

FMT = get_format("9cat_h2h")
CATS = [c.key for c in FMT.categories]


def setup():
    rosters, T = league()
    out = rosters[0][weakest(0, T, rosters[0], FMT, SPREAD)]
    cands = np.array(
        [
            line(),
            line(fgm=14, fga=22, reb=12),
            line(fgm=6, fga=20, fg3m=1, reb=11, blk=3),  # high volume, low percentage
            line(tov=0.5),
        ]
    )
    return T, out, cands


def test_rows_sum_to_the_net_score():
    T, out, cands = setup()
    by_cat = score_candidates_by_category(0, T, out, cands, FMT, SPREAD)
    assert np.allclose(
        by_cat.sum(axis=1), score_candidates(0, T, out, cands, FMT, SPREAD), atol=1e-9
    )


def test_shape_follows_the_format_categories():
    T, out, cands = setup()
    by_cat = score_candidates_by_category(0, T, out, cands, FMT, SPREAD)
    assert by_cat.shape == (len(cands), len(FMT.categories))
    one = score_candidates_by_category(0, T, out, cands[0], FMT, SPREAD)
    assert one.shape == (1, len(FMT.categories))


def test_fewer_turnovers_than_the_out_line_is_a_gain():
    T, out, _ = setup()
    cand = out.copy()
    cand[STATS.index("tov")] = out[STATS.index("tov")] - 1
    by_cat = score_candidates_by_category(0, T, out, cand, FMT, SPREAD)[0]
    assert by_cat[CATS.index("tov")] > 0
    others = [i for i, c in enumerate(CATS) if c != "tov"]
    assert np.allclose(by_cat[others], 0)


def test_low_percentage_volume_costs_fg_pct_while_counting_stats_gain():
    T, out, _ = setup()
    cand = out.copy()
    cand[STATS.index("fgm")] += 1
    cand[STATS.index("fga")] += 10  # one more make on ten more shots
    cand[STATS.index("reb")] += 4
    by_cat = score_candidates_by_category(0, T, out, cand, FMT, SPREAD)[0]
    assert by_cat[CATS.index("fg_pct")] < 0
    assert by_cat[CATS.index("reb")] > 0
    assert by_cat[CATS.index("pts")] > 0


def test_the_out_line_itself_scores_zero_everywhere():
    T, out, _ = setup()
    assert np.allclose(score_candidates_by_category(0, T, out, out, FMT, SPREAD), 0)


def test_deterministic():
    T, out, cands = setup()
    a = score_candidates_by_category(0, T, out, cands, FMT, SPREAD)
    b = score_candidates_by_category(0, T, out, cands, FMT, SPREAD)
    assert np.array_equal(a, b)
