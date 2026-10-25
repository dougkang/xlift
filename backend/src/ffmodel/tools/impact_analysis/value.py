"""xLift for a scenario: per-period lines, team totals, weekly spreads (007 research R2, R5, R6).

The maths is in `ffmodel.core.value`; this module turns a scenario and its projections into the
arrays it takes.
"""

import numpy as np

from ffmodel.core.scenario import from_snapshot
from ffmodel.core.scoring import ScoringFormat
from ffmodel.core.sim import STRATEGIC, category_values, simulate_team, strategic_k
from ffmodel.core.value import score_candidates, score_own, weakest
from ffmodel.tools.impact_analysis import cache

SPREAD_ITERATIONS = 4000
SPREAD_SEED = 20261024  # the rankings report's seed, so spreads match it (SC-001)


def lines(projections: dict, games_per_period: int) -> dict[int, np.ndarray]:
    """Expected per-period line: per-game mean × availability × games per period (FR-004).
    Players without games have no line."""
    return {
        pid: p.mean * (p.availability or 0.0) * games_per_period
        for pid, p in projections.items()
        if p.games_found > 0
    }


def team_totals(scenario, player_lines: dict, base_stats) -> tuple[list[int], np.ndarray]:
    """(team ids, T): each team's summed active lines, teams in id order."""
    team_ids = sorted(scenario.rosters)
    zero = np.zeros(len(base_stats))
    T = np.array(
        [
            sum((player_lines[p] for p in scenario.active_players(t) if p in player_lines), zero)
            for t in team_ids
        ]
    )
    return team_ids, T


def weekly_spread(scenario, projections: dict, fmt: ScoringFormat, games_per_period: int):
    """Per-category SD of two teams' weekly difference: √2 × the median over teams of one team's
    simulated per-period SD (FR-006). Seeded, so repeatable."""
    sds = []
    for t in sorted(scenario.rosters):
        team = [projections[p] for p in scenario.active_players(t) if p in projections]
        samples = simulate_team(
            t,
            team,
            strategic_k(games_per_period),
            fmt,
            iterations=SPREAD_ITERATIONS,
            seed=SPREAD_SEED,
            mode_code=STRATEGIC,
        )
        sds.append(np.nanstd(category_values(samples, fmt), axis=0))
    return np.sqrt(2) * np.nan_to_num(np.nanmedian(np.array(sds), axis=0))


def _out_line(scenario, team_id, ti, T, player_lines, fmt, spread) -> np.ndarray:
    """Who makes room: an open active slot, else the weakest active player (FR-005). A player
    with no line counts as an empty slot."""
    zero = np.zeros(T.shape[1])
    active = scenario.active_players(team_id)
    if scenario.open_active_slots(team_id) > 0 or any(p not in player_lines for p in active):
        return zero
    if not active:
        return zero
    L = np.array([player_lines[p] for p in active])
    return L[weakest(ti, T, L, fmt, spread)]


def score_rows(
    scenario, projections: dict, fmt: ScoringFormat, games_per_period: int, spread
) -> dict[int, dict[int, float | None]]:
    """{team: {player: xLift for that team}} for every roster player (FR-002, FR-009, FR-011).

    Active players are scored against a copy of the team's weakest; reserve players as if they
    replaced it. Players without a line get None."""
    pl = lines(projections, games_per_period)
    team_ids, T = team_totals(scenario, pl, fmt.base_stats)
    out: dict[int, dict[int, float | None]] = {}
    for ti, t in enumerate(team_ids):
        out_line = _out_line(scenario, t, ti, T, pl, fmt, spread)
        active = set(scenario.active_players(t))
        rows: dict[int, float | None] = {}
        own = [p for p in active if p in pl]
        if own:
            vals = score_own(ti, T, np.array([pl[p] for p in own]), out_line, fmt, spread)
            rows |= {p: float(v) for p, v in zip(own, vals, strict=True)}
        cands = [s.player_id for s in scenario.rosters[t] if s.player_id not in active]
        cands = [p for p in cands if p in pl]
        if cands:
            vals = score_candidates(ti, T, out_line, np.array([pl[p] for p in cands]), fmt, spread)
            rows |= {p: float(v) for p, v in zip(cands, vals, strict=True)}
        out[t] = {s.player_id: rows.get(s.player_id) for s in scenario.rosters[t]}
    return out


def score_pool(
    scenario,
    team_id: int,
    pool_projections: dict,
    fmt: ScoringFormat,
    games_per_period: int,
    spread,
    roster_projections: dict,
) -> dict[int, float | None]:
    """{player: xLift for `team_id`} for picker candidates, each swapped in for the team's
    weakest active player (FR-001, FR-010). `roster_projections` covers every rostered player,
    so team totals are complete."""
    pl = lines(roster_projections, games_per_period)
    team_ids, T = team_totals(scenario, pl, fmt.base_stats)
    ti = team_ids.index(team_id)
    out_line = _out_line(scenario, team_id, ti, T, pl, fmt, spread)
    cand = lines(pool_projections, games_per_period)
    ids = list(cand)
    out: dict[int, float | None] = dict.fromkeys(pool_projections)
    if ids:
        vals = score_candidates(ti, T, out_line, np.array([cand[p] for p in ids]), fmt, spread)
        out |= {p: float(v) for p, v in zip(ids, vals, strict=True)}
    return out


def identity(projections: dict, scenario) -> dict:
    return projections


def league_spread(conn, fmt: ScoringFormat, s, snapshot, prepare=identity):
    """The cached weekly spread for settings `s`, from the no-move scenario (research R2).

    `prepare(projections, scenario)` applies the Fragility Penalty before simulating."""
    base = from_snapshot(snapshot)

    def compute():
        rostered = [spot.player_id for spots in base.rosters.values() for spot in spots]
        proj = prepare(cache.projections(conn, rostered, fmt, s), base)
        return weekly_spread(base, proj, fmt, s.games_per_period)

    return cache.spread(conn, fmt, s, compute)
