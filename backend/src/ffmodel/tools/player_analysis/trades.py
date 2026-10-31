"""The Trade Finder (014): for each other team, the most balanced 1-for-1 trade that raises both
teams' expected weekly category wins.

Uses the league as imported, never Impact Analysis's moves, and imports core only
(Constitution VII). The search, the pick and the order are all here; the frontend only draws.
"""

import numpy as np
from sqlalchemy.exc import NoResultFound

from ffmodel.core import cache
from ffmodel.core.data import get_league
from ffmodel.core.model import fragility
from ffmodel.core.scenario import from_snapshot
from ffmodel.core.scoring import UnsupportedFormat, get_format
from ffmodel.core.value import trade_grid
from ffmodel.tools.player_analysis.leaderboard import NotFound
from ffmodel.tools.player_analysis.settings import PlayerAnalysisSettings, normalize

# A gain must show as at least +0.01 at the page's two decimals, or it isn't a gain (FR-003).
MIN_GAIN = 0.005


def find_trades(conn, settings: PlayerAnalysisSettings) -> dict:
    s = normalize(settings)
    try:
        snapshot = get_league(conn, s.league_id)
    except NoResultFound as exc:
        raise NotFound(f"no league {s.league_id}") from exc
    teams = {t.fantasy_team_id: t for t in snapshot.teams}
    if s.team_id not in teams:
        raise NotFound(f"no team {s.team_id} in league {s.league_id}")
    scenario = from_snapshot(snapshot)
    out = {
        "settings": {
            "mode": s.mode,
            "window": s.window,
            "as_of": s.as_of,
            "fragility": s.fragility,
        },
        "team_id": s.team_id,
        "team_name": teams[s.team_id].name,
        "categories": [],
        "rows": [],
        "warnings": [],
    }
    try:
        fmt = get_format(scenario.league.scoring_format_id)
    except UnsupportedFormat:
        out["warnings"].append(
            {
                "code": "UNSUPPORTED_FORMAT",
                "message": f"Scoring format '{scenario.league.scoring_format_id}'"
                " is not supported.",
            }
        )
        return out
    out["categories"] = [
        {"key": c.key, "label": c.label, "higher_is_better": c.higher_is_better}
        for c in fmt.categories
    ]

    roster = {r.player.player_id: r for t in snapshot.teams for r in t.roster}
    statuses = {pid: r.status for pid, r in roster.items()}

    def penalize(proj, sc):  # the Fragility Penalty (007 FR-013), as everywhere else
        return fragility.apply(s.fragility, proj, sc, statuses, conn, s.as_of)

    projections = penalize(cache.projections(conn, list(roster), fmt, s), scenario)
    spread = cache.league_spread(conn, fmt, s, snapshot, penalize)

    def player(pid: int) -> dict:
        p = roster[pid]
        return {
            "player_id": pid,
            "name": p.player.full_name,
            "nba_team": p.player.current_team,
            "status": p.status,
        }

    rows = []
    for tid, team in teams.items():
        if tid == s.team_id:
            continue
        mine, theirs, gain_a, gain_b, by_cat = trade_grid(
            scenario, s.team_id, tid, projections, fmt, s.games_per_period, spread
        )
        trade = None
        both = (gain_a >= MIN_GAIN) & (gain_b >= MIN_GAIN)
        if both.any():
            # The most balanced win-win: largest smaller gain, then largest total, then names.
            names = {p: roster[p].player.full_name for p in (*mine, *theirs)}
            pairs = [(i, j) for i, j in zip(*np.nonzero(both), strict=True)]
            i, j = min(
                pairs,
                key=lambda ij: (
                    -min(gain_a[ij], gain_b[ij]),
                    -(gain_a[ij] + gain_b[ij]),
                    names[mine[ij[0]]],
                    names[theirs[ij[1]]],
                ),
            )
            # Every category, in the format's order: one column each on the page.
            cats = [(c.key, float(by_cat[i, j, k])) for k, c in enumerate(fmt.categories)]
            trade = {
                "give": player(mine[i]),
                "get": player(theirs[j]),
                "your_gain": float(gain_a[i, j]),
                "their_gain": float(gain_b[i, j]),
                "your_categories": [{"category": k, "gain": g} for k, g in cats],
            }
        rows.append(
            {"team_id": tid, "team_name": team.name, "manager": team.manager, "trade": trade}
        )
    rows.sort(
        key=lambda r: (
            r["trade"] is None,
            -min(r["trade"]["your_gain"], r["trade"]["their_gain"]) if r["trade"] else 0.0,
            r["team_name"],
        )
    )
    out["rows"] = rows
    return out
