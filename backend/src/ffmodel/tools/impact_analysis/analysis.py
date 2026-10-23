"""Impact Analysis orchestration: scenario + projections + simulation → result (contracts/api.md).

Returns plain JSON-ready dicts; the API layer validates them against its Pydantic models.
"""

from collections.abc import Sequence

import numpy as np
from sqlalchemy.exc import NoResultFound

from ffmodel.core.data import get_data_freshness, get_league
from ffmodel.core.scenario import Scenario, from_snapshot
from ffmodel.core.scoring import ScoringFormat, UnsupportedFormat, get_format
from ffmodel.core.sim import (
    STRATEGIC,
    category_values,
    density_curves,
    matchup_odds,
    projected_averages,
    ranks,
    record,
    simulate_team,
    strategic_k,
)
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.settings import AnalysisSettings, normalize

FOOTNOTE_MARKER = "*"


class NotFound(LookupError):
    pass


def _odds(o) -> dict:
    return {"win": o.win, "tie": o.tie, "loss": o.loss}


def _num(v) -> float | None:
    return None if v is None or not np.isfinite(v) else float(v)


def _settings_echo(s: AnalysisSettings) -> dict:
    return {
        "mode": s.mode,
        "window": s.window,
        "as_of": s.as_of,
        "iterations": s.iterations,
        "seed": s.seed,
        "opponent_id": s.opponent_id,
        "period_start": s.period_start,
        "period_end": s.period_end,
    }


def _player_info(snapshot) -> dict[int, dict]:
    info = {}
    for team in snapshot.teams:
        for r in team.roster:
            info[r.player.player_id] = {"player": r.player, "status": r.status}
    return info


def _roster_rows(scenario: Scenario, snapshot, info, projections, games_remaining: bool) -> list:
    base_owner = {r.player.player_id: t.fantasy_team_id for t in snapshot.teams for r in t.roster}
    rows = []
    for team in snapshot.teams:
        tid = team.fantasy_team_id
        players = []
        for spot in scenario.rosters[tid]:
            p = info[spot.player_id]["player"]
            proj = projections.get(spot.player_id)
            found = proj.games_found if proj else 0
            requested = proj.games_requested if proj else 0
            players.append(
                {
                    "player_id": p.player_id,
                    "name": p.full_name,
                    "nba_team": p.current_team,
                    "positions": list(p.positions),
                    "slot": spot.slot,
                    "status": info[spot.player_id]["status"],
                    "games_found": found,
                    "games_requested": requested,
                    "games_remaining": proj.games_remaining if (proj and games_remaining) else None,
                    "footnote_marker": FOOTNOTE_MARKER if proj and proj.is_short else None,
                    "moved": base_owner.get(p.player_id) != tid,
                }
            )
        rows.append(
            {
                "team_id": tid,
                "team_name": team.name,
                "manager": team.manager,
                "open_active_slots": scenario.open_active_slots(tid),
                "players": players,
            }
        )
    return rows


def _footnotes(roster_rows: list, team_id: int) -> list:
    team = next(r for r in roster_rows if r["team_id"] == team_id)
    return [
        {
            "marker": FOOTNOTE_MARKER,
            "player_id": p["player_id"],
            "text": f"{FOOTNOTE_MARKER} {p['games_found']} of {p['games_requested']} games",
        }
        for p in team["players"]
        if p["footnote_marker"]
    ]


_RESULT = {(1, 0, 0): "win", (0, 1, 0): "loss", (0, 0, 1): "tie"}


def _rec(r) -> dict:
    return {"wins": r.wins, "losses": r.losses, "ties": r.ties}


def _matchup_row(o, fmt: ScoringFormat, names: dict, teams: dict) -> dict:
    """One opponent: odds, projected category record, and the projected matchup result."""
    cat_rec = record(o.categories)
    m = record([o.matchup])
    return {
        "opponent_id": o.opponent_id,
        "opponent_name": names[o.opponent_id],
        "opponent_manager": teams[o.opponent_id].manager,
        "matchup": _odds(o.matchup),
        "categories": {
            c.key: _odds(co) for c, co in zip(fmt.categories, o.categories, strict=True)
        },
        "category_record": _rec(cat_rec),
        "result": _RESULT[(m.wins, m.losses, m.ties)],
    }


def _totals(rows: list) -> dict:
    """Total row for the record table: matchup W-L-T and summed category W-L-T."""
    results = [r["result"] for r in rows]
    cats = [r["category_record"] for r in rows]
    return {
        "matchups": {
            "wins": results.count("win"),
            "losses": results.count("loss"),
            "ties": results.count("tie"),
        },
        "categories": {k: sum(c[k] for c in cats) for k in ("wins", "losses", "ties")},
    }


def _league_average(samples: dict, fmt: ScoringFormat) -> np.ndarray:
    """Projected average of the pooled league (ratios stay ratio-of-means, Constitution I)."""
    stats = next(iter(samples.values())).totals.keys()
    pooled = {st: np.concatenate([ts.totals[st] for ts in samples.values()]) for st in stats}
    return fmt.projected_average(pooled)


def _leader(team_ranks: dict, i: int, exclude: int | None = None) -> int | None:
    teams = [t for t in team_ranks if t != exclude]
    return min(teams, key=lambda t: (team_ranks[t][i], t)) if teams else None


def _curves(
    fmt: ScoringFormat,
    values: dict,
    averages: dict,
    league_avg: np.ndarray,
    team_ranks: dict,
    names: dict,
    selected: int,
    seed: int,
) -> list:
    curves = []
    for i, cat in enumerate(fmt.categories):
        # role -> (team_id, label, samples, mean); means are projected averages (ratio of means).
        roles = {
            "selected": (selected, names[selected], values[selected][:, i], averages[selected][i])
        }
        if team_ranks[selected][i] == 1:
            best = _leader(team_ranks, i, exclude=selected)
            if best is not None:
                roles["next_best"] = (best, names[best], values[best][:, i], averages[best][i])
        else:
            leader = _leader(team_ranks, i)
            roles["leader"] = (leader, names[leader], values[leader][:, i], averages[leader][i])
        pooled = np.concatenate([v[:, i] for v in values.values()])
        roles["league_average"] = (None, "League average", pooled, league_avg[i])
        dens = density_curves({r: v for r, (_, _, v, _) in roles.items()}, seed=seed)
        curves.append(
            {
                "category": cat.key,
                "x": [float(x) for x in dens["x"]],
                "series": [
                    {
                        "role": r,
                        "team_id": tid,
                        "label": label,
                        "mean": _num(mean),
                        "density": [float(d) for d in dens["series"][r]],
                    }
                    for r, (tid, label, _, mean) in roles.items()
                ],
            }
        )
    return curves


def analyze(conn, settings: AnalysisSettings, moves: Sequence = ()) -> dict:
    s = normalize(settings)
    try:
        snapshot = get_league(conn, s.league_id)
    except NoResultFound as exc:
        raise NotFound(f"no league {s.league_id}") from exc
    teams = {t.fantasy_team_id: t for t in snapshot.teams}
    if s.team_id not in teams:
        raise NotFound(f"no team {s.team_id} in league {s.league_id}")

    scenario = from_snapshot(snapshot)
    info = _player_info(snapshot)
    names = {tid: t.name for tid, t in teams.items()}
    selected = teams[s.team_id]
    freshness = get_data_freshness(conn, s.league_id).__dict__
    result = {
        "settings": _settings_echo(s),
        "header": {
            "team_id": s.team_id,
            "team_name": selected.name,
            "manager": selected.manager,
            "record": None,
            "matchup_win_probability": None,
        },
        "categories": [],
        "radar": None,
        "category_table": None,
        "curves": [],
        "matchups": [],
        "matchup_totals": None,
        "rosters": [],
        "footnotes": [],
        "warnings": [],
        "freshness": freshness,
    }

    try:
        fmt = get_format(scenario.league.scoring_format_id)
    except UnsupportedFormat:
        result["warnings"].append(
            {
                "code": "UNSUPPORTED_FORMAT",
                "message": f"Scoring format '{scenario.league.scoring_format_id}'"
                " is not supported.",
            }
        )
        result["rosters"] = _roster_rows(scenario, snapshot, info, {}, False)
        return result

    result["categories"] = [
        {
            "key": c.key,
            "label": c.label,
            "decimals": c.decimals,
            "higher_is_better": c.higher_is_better,
        }
        for c in fmt.categories
    ]
    rostered = [spot.player_id for spots in scenario.rosters.values() for spot in spots]
    projections = cache.projections(conn, rostered, fmt, s)

    k = strategic_k(s.games_per_period)
    samples = {
        tid: simulate_team(
            tid,
            [projections[p] for p in scenario.active_players(tid)],
            k,
            fmt,
            iterations=s.iterations,
            seed=s.seed,
            mode_code=STRATEGIC,
        )
        for tid in teams
    }
    values = {tid: category_values(ts, fmt) for tid, ts in samples.items()}
    averages = {tid: projected_averages(ts, fmt) for tid, ts in samples.items()}
    team_ranks = ranks(averages, fmt)

    odds = [
        matchup_odds(s.team_id, values[s.team_id], tid, values[tid], fmt)
        for tid in teams
        if tid != s.team_id
    ]
    rec = record(o.matchup for o in odds)
    result["header"]["record"] = {
        "wins": rec.wins,
        "losses": rec.losses,
        "ties": rec.ties,
        "unit": "matchups",
    }
    result["matchups"] = [_matchup_row(o, fmt, names, teams) for o in odds]
    result["matchup_totals"] = _totals(result["matchups"])
    result["radar"] = {
        "team_count": len(teams),
        "series": [
            {
                "team_id": tid,
                "team_name": names[tid],
                "emphasis": "selected" if tid == s.team_id else "other",
                "ranks": team_ranks[tid],
            }
            for tid in teams
        ],
    }
    league_avg = _league_average(samples, fmt)
    leaders = [_leader(team_ranks, i) for i in range(len(fmt.categories))]
    result["category_table"] = {
        "kind": "ranks",
        "rows": [
            {
                "category": c.key,
                "rank": team_ranks[s.team_id][i],
                "average": _num(averages[s.team_id][i]),
                "league_average": _num(league_avg[i]),
                "leader_team_id": leaders[i],
                "leader_name": names[leaders[i]],
                "leader_average": _num(averages[leaders[i]][i]),
            }
            for i, c in enumerate(fmt.categories)
        ],
    }
    result["curves"] = _curves(
        fmt, values, averages, league_avg, team_ranks, names, s.team_id, s.seed
    )
    result["rosters"] = _roster_rows(scenario, snapshot, info, projections, False)
    result["footnotes"] = _footnotes(result["rosters"], s.team_id)
    return result
