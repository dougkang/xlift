"""SC-004 / Constitution IV: the docs' streaming example, on synthetic projections."""

import pytest

from ffmodel.core.sim import (
    STRATEGIC,
    TACTICAL,
    category_values,
    matchup_odds,
    simulate_team,
    strategic_k,
    tactical_k,
)
from tests.sim_helpers import FMT, projection

CORE = [projection(1, games_remaining=2), projection(2, games_remaining=2)]
OPPONENT = [projection(i, games_remaining=2) for i in (20, 21, 22)]


def win_prob(extra, mode, seed):
    k, code = (tactical_k, TACTICAL) if mode == "tactical" else (strategic_k(3), STRATEGIC)
    mine = simulate_team(1, CORE + [extra], k, FMT, iterations=20_000, seed=seed, mode_code=code)
    theirs = simulate_team(2, OPPONENT, k, FMT, iterations=20_000, seed=seed, mode_code=code)
    return matchup_odds(
        1, category_values(mine, FMT), 2, category_values(theirs, FMT), FMT
    ).matchup.win


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_more_games_wins_tactically_better_player_wins_strategically(seed):
    busy = projection(50, 0.9, games_remaining=2)  # slightly worse, 2 games left
    steady = projection(50, 1.0, games_remaining=1)  # slightly better, 1 game left
    assert win_prob(busy, "tactical", seed) > win_prob(steady, "tactical", seed)
    assert win_prob(steady, "strategic", seed) > win_prob(busy, "strategic", seed)
