from datetime import date

import numpy as np
import pytest

from ffmodel.core.data.models import GameWindow, PlayerGameLine
from ffmodel.core.model import availability_rate, fit_projection

STATS = ("fgm", "fga", "ast")


def line(i, fgm, fga, ast):
    return PlayerGameLine(
        game_id=i,
        season_id="2026-27",
        game_date=date(2026, 11, i),
        team="BOS",
        opponent="MIA",
        minutes=30.0,
        fgm=fgm,
        fga=fga,
        fg3m=0,
        fg3a=0,
        ftm=0,
        fta=0,
        oreb=0,
        dreb=0,
        reb=0,
        ast=ast,
        stl=0,
        blk=0,
        tov=0,
        pf=0,
        pts=2 * fgm,
        plus_minus=0,
    )


def window(rows, requested=15):
    games = tuple(line(i + 1, *r) for i, r in enumerate(rows))
    return GameWindow(player_id=1, requested=requested, found=len(games), games=games)


def test_fit_three_games():
    rows = [(5, 10, 2), (7, 14, 4), (6, 12, 6)]
    p = fit_projection(1, window(rows), STATS)
    x = np.array(rows, float)
    np.testing.assert_allclose(p.mean, x.mean(0))
    lam = 5 / 7
    sigma = (1 - lam) * np.cov(x, rowvar=False) + lam * np.diag(np.maximum(x.mean(0), 0.25))
    np.testing.assert_allclose(p.chol @ p.chol.T, sigma, atol=1e-8)
    assert p.is_short and p.games_found == 3


def test_single_game_uses_prior_only():
    p = fit_projection(1, window([(0, 3, 0)]), STATS)
    np.testing.assert_allclose(p.chol @ p.chol.T, np.diag([0.25, 3, 0.25]), atol=1e-8)


def test_two_games_rank_deficient_is_fine():
    p = fit_projection(1, window([(5, 10, 2), (6, 11, 3)]), STATS)
    assert p.chol is not None and np.all(np.isfinite(p.chol))


def test_no_games():
    p = fit_projection(1, window([]), STATS)
    assert p.chol is None and p.is_short and (p.mean == 0).all()


@pytest.mark.parametrize(
    ("played", "team", "rate"), [(0, 5, None), (5, 0, 1.0), (6, 10, 0.6), (11, 10, 1.0)]
)
def test_availability(played, team, rate):
    assert availability_rate(played, team) == rate
