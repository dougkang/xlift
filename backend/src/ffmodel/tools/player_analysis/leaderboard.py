"""The xLift leaderboard (009): players ranked by xLift, broken down by category.

Uses the league as imported, never Impact Analysis's moves (FR-005), and imports core only
(Constitution VII). Eligibility, filters, ordering and the top n are all here, so the frontend
only draws (FR-009, research R6).
"""

import numpy as np
from sqlalchemy.exc import NoResultFound

from ffmodel.core import cache
from ffmodel.core.data import get_league, get_player_details
from ffmodel.core.model import fragility
from ffmodel.core.scenario import from_snapshot
from ffmodel.core.scoring import UnsupportedFormat, get_format
from ffmodel.core.value import (
    score_league_by_category,
    score_pool_by_category,
    score_team_by_category,
)
from ffmodel.tools.player_analysis.settings import (
    LeaderboardQuery,
    PlayerAnalysisSettings,
    normalize,
)

FOOTNOTE_MARKER = "*"
FREE_AGENT = "Free agent"


class NotFound(LookupError):
    pass


def leaderboard(conn, settings: PlayerAnalysisSettings, query: LeaderboardQuery) -> dict:
    s = normalize(settings)
    try:
        snapshot = get_league(conn, s.league_id)
    except NoResultFound as exc:
        raise NotFound(f"no league {s.league_id}") from exc
    names = {t.fantasy_team_id: t.name for t in snapshot.teams}
    if s.team_id not in names:
        raise NotFound(f"no team {s.team_id} in league {s.league_id}")
    one_team = query.pool if isinstance(query.pool, int) else None  # a team's players only
    if one_team is not None and one_team not in names:
        raise NotFound(f"no team {one_team} in league {s.league_id}")
    scenario = from_snapshot(snapshot)
    out = {
        "settings": {
            "mode": s.mode,
            "window": s.window,
            "as_of": s.as_of,
            "fragility": s.fragility,
        },
        "evaluate_for": query.evaluate_for,
        "team_id": s.team_id,
        "team_name": names[s.team_id],
        "categories": [],
        "total": 0,
        "entries": [],
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

    # The picker's pool: league players plus everyone rostered, with the rostered players'
    # latest statuses, so the Fragility Penalty's tags match Impact Analysis (research R6).
    rostered_info = {
        r.player.player_id: (r.player, r.status) for t in snapshot.teams for r in t.roster
    }
    pool = get_player_details(conn, league_id=s.league_id) | rostered_info
    owner = scenario.owner
    candidates = []
    for pid, (summary, _status) in pool.items():
        team = owner.get(pid)
        if team is None and not summary.is_active:
            continue
        if team is not None and query.pool == "free_agents":
            continue
        if one_team is not None and team != one_team:
            continue
        candidates.append(pid)

    statuses = {pid: status for pid, (_, status) in pool.items()}

    def penalize(proj, sc):  # the Fragility Penalty (007 FR-013)
        return fragility.apply(s.fragility, proj, sc, statuses, conn, s.as_of)

    rostered = list(rostered_info)
    projections = penalize(
        cache.projections(conn, set(candidates) | set(rostered), fmt, s), scenario
    )
    spread = cache.league_spread(conn, fmt, s, snapshot, penalize)
    roster_proj = {pid: projections[pid] for pid in rostered}
    pool_proj = {pid: projections[pid] for pid in candidates}
    if query.evaluate_for == "league":  # position-neutral (FR-008, research R3)
        scores = score_league_by_category(
            scenario, pool_proj, fmt, s.games_per_period, spread, roster_proj
        )
    else:
        # Other players replace the team's weakest active player; the team's own roster is
        # valued against that weakest player, as Impact Analysis values it (one scale).
        others = {p: v for p, v in pool_proj.items() if owner.get(p) != s.team_id}
        scores = score_pool_by_category(
            scenario, s.team_id, others, fmt, s.games_per_period, spread, roster_proj
        )
        if any(owner.get(p) == s.team_id for p in candidates):
            scores |= score_team_by_category(
                scenario, s.team_id, fmt, s.games_per_period, spread, roster_proj
            )

    rows = []
    for pid in candidates:
        by_cat, proj = scores.get(pid), projections[pid]
        if by_cat is None or proj.games_found < query.min_games:
            continue
        summary, status = pool[pid]
        team = owner.get(pid)
        short = proj.games_found < proj.games_requested
        rows.append(
            {
                "player_id": pid,
                "name": summary.full_name,
                "nba_team": summary.current_team,
                "owner_team_id": team,
                "owner_label": names[team] if team is not None else FREE_AGENT,
                "status": status,
                "games_found": proj.games_found,
                "games_requested": proj.games_requested,
                "footnote": (
                    f"{FOOTNOTE_MARKER} {proj.games_found} of {proj.games_requested} games"
                    if short
                    else None
                ),
                "xlift": float(np.sum(by_cat)),
                "by_category": [float(v) for v in by_cat],
            }
        )
    rows.sort(key=lambda r: (-r["xlift"], r["name"], r["player_id"]))
    out["total"] = len(rows)
    out["entries"] = rows if query.top is None else rows[: query.top]
    return out
