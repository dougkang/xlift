"""Impact Analysis orchestration: scenario + projections + simulation → result (contracts/api.md).

Returns plain JSON-ready dicts; the API layer validates them against its Pydantic models.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

import numpy as np

from ffmodel.core.data import count_team_games_bulk, get_data_freshness, get_matchup_state
from ffmodel.core.scenario import Scenario
from ffmodel.core.scoring import ScoringFormat, UnsupportedFormat, get_format
from ffmodel.core.sim import (
    STRATEGIC,
    TACTICAL,
    MissingStats,
    Record,
    actual_values,
    base_vector,
    category_values,
    current_record,
    density_curves,
    expected_record,
    league_shape,
    matchup_odds,
    projected_averages,
    ranks,
    record,
    simulate_team,
    strategic_k,
    tactical_k,
    whole_record,
)
from ffmodel.tools.impact_analysis import cache, fragility, value
from ffmodel.tools.impact_analysis.changes import build_changes
from ffmodel.tools.impact_analysis.settings import AnalysisSettings, normalize
from ffmodel.tools.impact_analysis.state import NotFound, load_state

__all__ = ["NotFound", "analyze"]

FOOTNOTE_MARKER = "*"


@dataclass(eq=False)
class Computed:
    """Simulation internals for one scenario (003 research R1): enough to render, diff, and
    reuse untouched teams' samples."""

    active: dict  # team -> frozenset of active player ids
    samples: dict
    values: dict
    averages: dict
    team_ranks: dict
    normalized: dict
    win_rates: dict
    area_scores: dict


def _compute(
    s, fmt, scenario, projections, teams, reuse: "Computed | None" = None, bases: dict | None = None
) -> Computed:
    """`bases` (tactical, 005): each team's week-to-date totals, added to its simulated games."""
    k, mode_code = (
        (tactical_k, TACTICAL)
        if s.mode == "tactical"
        else (strategic_k(s.games_per_period), STRATEGIC)
    )
    active = {tid: frozenset(scenario.active_players(tid)) for tid in teams}
    samples, values, averages = {}, {}, {}
    for tid in teams:
        if reuse is not None and reuse.active.get(tid) == active[tid]:
            # Same active players, mode, seed and iterations: bit-identical samples (R1).
            samples[tid] = reuse.samples[tid]
            values[tid] = reuse.values[tid]
            averages[tid] = reuse.averages[tid]
            continue
        samples[tid] = simulate_team(
            tid,
            [projections[p] for p in scenario.active_players(tid)],
            k,
            fmt,
            iterations=s.iterations,
            seed=s.seed,
            mode_code=mode_code,
            base=(bases or {}).get(tid),
        )
        values[tid] = category_values(samples[tid], fmt)
        averages[tid] = projected_averages(samples[tid], fmt)
    team_ranks = ranks(averages, fmt)
    normalized = _normalized(averages, fmt)
    win_rates = _win_rates(values, fmt)
    return Computed(
        active,
        samples,
        values,
        averages,
        team_ranks,
        normalized,
        win_rates,
        _area_scores(team_ranks, normalized, win_rates),
    )


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
        "fragility": s.fragility,
        "opponent_id": s.opponent_id,
        "period_start": s.period_start,
        "period_end": s.period_end,
    }


def _roster_rows(
    scenario: Scenario, snapshot, info, projections, games_remaining: bool, xlift=None
) -> list:
    """`xlift`: {team: {player: value for that team}} (007 FR-009, FR-011)."""
    xlift = xlift or {}
    base_owner = {r.player.player_id: t.fantasy_team_id for t in snapshot.teams for r in t.roster}
    rows = []
    for team in snapshot.teams:
        tid = team.fantasy_team_id
        players = []
        for spot in scenario.rosters[tid]:
            p, status = info[spot.player_id]
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
                    "status": status,
                    "games_found": found,
                    "games_requested": requested,
                    "games_remaining": proj.games_remaining if (proj and games_remaining) else None,
                    "footnote_marker": FOOTNOTE_MARKER if proj and proj.is_short else None,
                    "moved": base_owner.get(p.player_id) != tid,
                    "xlift": xlift.get(tid, {}).get(p.player_id),
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


def _footnotes(roster_rows: list, team_ids: Sequence[int]) -> list:
    """Short-history notes for the rosters on screen: yours, plus the opponent's in tactical."""
    return [
        {
            "marker": FOOTNOTE_MARKER,
            "player_id": p["player_id"],
            "text": f"{FOOTNOTE_MARKER} {p['games_found']} of {p['games_requested']} games",
        }
        for team_id in team_ids
        for team in roster_rows
        if team["team_id"] == team_id
        for p in team["players"]
        if p["footnote_marker"]
    ]


_RESULT = {(1, 0, 0): "win", (0, 1, 0): "loss", (0, 0, 1): "tie"}


def _rec(r) -> dict:
    return {"wins": r.wins, "losses": r.losses, "ties": r.ties}


def _expected(r, whole=None) -> dict:
    """An expected category record, unrounded, with its standings win % (010 R2), and the whole
    record the page shows (`whole`, or `r` in whole categories, 010 R4)."""
    return {
        "wins": r.wins,
        "losses": r.losses,
        "ties": r.ties,
        "win_pct": r.win_pct,
        "record": _rec(whole or whole_record(r)),
    }


def _sum_records(rows: list) -> Record:
    """The whole records of the H2H rows, added up: the Total the table shows."""
    recs = [r["expected_record"]["record"] for r in rows]
    return Record(*(sum(c[k] for c in recs) for k in ("wins", "losses", "ties")))


def _matchup_row(o, fmt: ScoringFormat, names: dict, teams: dict) -> dict:
    """One opponent: odds, projected category record, and the projected matchup result.

    Under each-category standings there is no matchup result; the expected category record is
    what the matchup adds to the standings (010 R3).
    """
    cat_rec = record(o.categories)
    m = record([o.matchup])
    each = fmt.standings == "category"
    return {
        "opponent_id": o.opponent_id,
        "opponent_name": names[o.opponent_id],
        "opponent_manager": teams[o.opponent_id].manager,
        "matchup": _odds(o.matchup),
        "categories": {
            c.key: _odds(co) for c, co in zip(fmt.categories, o.categories, strict=True)
        },
        "category_record": _rec(cat_rec),
        "result": None if each else _RESULT[(m.wins, m.losses, m.ties)],
        "expected_record": _expected(expected_record(o.categories)) if each else None,
    }


def _totals(rows: list, expected=None, whole=None) -> dict:
    """Total row for the record table: matchup W-L-T and summed category W-L-T.

    `expected` (each-category standings, 010): the expected record summed over opponents, which
    replaces the matchup W-L-T."""
    results = [r["result"] for r in rows]
    cats = [r["category_record"] for r in rows]
    return {
        "matchups": None
        if expected is not None
        else {
            "wins": results.count("win"),
            "losses": results.count("loss"),
            "ties": results.count("tie"),
        },
        "categories": {k: sum(c[k] for c in cats) for k in ("wins", "losses", "ties")},
        "expected": None if expected is None else _expected(expected, whole),
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
    originals: dict | None = None,
) -> list:
    """`originals`: role -> (values array, averages) for before/after curves (003 research R5)."""
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
        roles["league_average"] = (None, "League Average", pooled, league_avg[i])
        for role, (vals, avgs) in (originals or {}).items():
            roles[role] = (None, "Original", vals[:, i], avgs[i])
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
    matchup = get_matchup_state(conn, settings.league_id) if settings.mode == "tactical" else None
    s = normalize(settings, matchup)
    if not moves:
        result, _ = _analyze(conn, s, (), matchup=matchup)
        result["changes"] = None
        return result
    original, orig_comp = cache.original(conn, s, lambda: _analyze(conn, s, (), matchup=matchup))
    if orig_comp is None:  # unsupported format or no matchup state: nothing to compare
        result, _ = _analyze(conn, s, moves, matchup=matchup)
        result["changes"] = None
        return result
    result, comp = _analyze(conn, s, moves, reuse=orig_comp, matchup=matchup)
    result["changes"] = build_changes(original, result, orig_comp, comp, s)
    return result


def _analyze(
    conn, s: AnalysisSettings, moves: Sequence, reuse: Computed | None = None, matchup=None
):
    """One scenario's result dict and its internals (None when nothing was simulated).

    With `reuse` (the original), untouched teams reuse its samples and the curves include the
    selected team's original distribution (`selected_original`).
    """
    state = load_state(conn, s.league_id, s.team_id, moves)
    snapshot, teams, names, scenario = state.snapshot, state.teams, state.names, state.scenario
    info = state.info
    selected = teams[s.team_id]
    freshness = get_data_freshness(conn, s.league_id).__dict__
    result = {
        "settings": _settings_echo(s),
        "standings": "matchup",  # the format's rule, once it's known (010 FR-006)
        "header": {
            "team_id": s.team_id,
            "team_name": selected.name,
            "manager": selected.manager,
            "record": None,
            "expected_record": None,  # each-category standings (010)
            "matchup_win_probability": None,
        },
        "categories": [],
        "radar": None,
        "category_table": None,
        "curves": [],
        "league_shape": None,  # strategic only (008 FR-015)
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
        return result, None

    result["standings"] = fmt.standings
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
    statuses = {pid: status for pid, (_, status) in info.items()}

    def penalize(proj, sc):  # the Fragility Penalty, before every result (007 FR-013)
        return fragility.apply(s.fragility, proj, sc, statuses, conn, s.as_of)

    projections = penalize(cache.projections(conn, rostered, fmt, s), scenario)
    tactical = s.mode == "tactical"
    # xLift uses the league-level weekly definition in both modes (007 FR-018, research R2).
    spread = value.league_spread(conn, fmt, s, snapshot, penalize)
    xlift = value.score_rows(scenario, projections, fmt, s.games_per_period, spread)
    result["rosters"] = _roster_rows(scenario, snapshot, info, projections, tactical, xlift)
    shown = [s.team_id] + ([s.opponent_id] if tactical and s.opponent_id else [])
    result["footnotes"] = _footnotes(result["rosters"], shown)

    bases = None
    if tactical:
        if matchup is None or s.opponent_id is None:
            result["warnings"].append(
                {
                    "code": "MATCHUP_NOT_LOADED",
                    "message": "This week's matchup hasn't been loaded yet.",
                }
            )
            return result, None
        if s.opponent_id not in teams:
            raise NotFound(f"no team {s.opponent_id} in league {s.league_id}")
        try:
            bases = {t: base_vector(line, fmt) for t, line in matchup.lines.items() if t in teams}
        except MissingStats as exc:
            result["warnings"].append(
                {
                    "code": "MATCHUP_STATS_MISSING",
                    "message": f"The matchup state lacks {', '.join(exc.names)}.",
                }
            )
            return result, None
        result["warnings"] += _matchup_warnings(conn, s, scenario, freshness)

    comp = _compute(s, fmt, scenario, projections, teams, reuse, bases)
    samples, values, averages = comp.samples, comp.values, comp.averages
    team_ranks, normalized, win_rates = comp.team_ranks, comp.normalized, comp.win_rates
    area_scores = comp.area_scores
    originals = {}
    if reuse is not None:
        originals["selected_original"] = (reuse.values[s.team_id], reuse.averages[s.team_id])

    if tactical:
        _tactical_results(
            result,
            s,
            matchup,
            fmt,
            scenario,
            projections,
            values,
            averages,
            team_ranks,
            names,
            teams,
            normalized,
            win_rates,
            area_scores,
            originals,
        )
        return result, comp

    odds = [
        matchup_odds(s.team_id, values[s.team_id], tid, values[tid], fmt)
        for tid in teams
        if tid != s.team_id
    ]
    result["matchups"] = [_matchup_row(o, fmt, names, teams) for o in odds]
    if fmt.standings == "category":
        # Each category is a W, L or T in the standings: the expected category record summed
        # over every opponent (010 FR-007).
        total = sum((expected_record(o.categories) for o in odds), expected_record(()))
        whole = _sum_records(result["matchups"])  # so the headline is the H2H Total
        result["header"]["expected_record"] = _expected(total, whole)
        result["matchup_totals"] = _totals(result["matchups"], total, whole)
    else:
        rec = record(o.matchup for o in odds)
        result["header"]["record"] = {
            "wins": rec.wins,
            "losses": rec.losses,
            "ties": rec.ties,
            "unit": "matchups",
        }
        result["matchup_totals"] = _totals(result["matchups"])
    result["radar"] = {
        "team_count": len(teams),
        "series": [
            {
                "team_id": tid,
                "team_name": names[tid],
                "emphasis": "selected" if tid == s.team_id else "other",
                "ranks": team_ranks[tid],
                "normalized": normalized[tid],
                "win_rate": win_rates[tid],
                "area": area_scores[tid],
                "averages": [_num(v) for v in averages[tid]],
            }
            for tid in teams
        ],
    }
    league_avg = _league_average(samples, fmt)
    leaders = [_leader(team_ranks, i) for i in range(len(fmt.categories))]
    result["radar"]["league"] = _radar_league(fmt, averages, league_avg, win_rates)
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
                "win_rate": win_rates[s.team_id][i],
            }
            for i, c in enumerate(fmt.categories)
        ],
    }
    result["curves"] = _curves(
        fmt, values, averages, league_avg, team_ranks, names, s.team_id, s.seed, originals
    )
    result["league_shape"] = _league_shape(fmt, comp, names, s.team_id, reuse)
    return result, comp


def _league_shape(fmt: ScoringFormat, comp: Computed, names: dict, selected: int, reuse) -> list:
    """Each category's league shape with names, the selected team's climb and cushion marks,
    and, with moves, its pre-move place (008 research R4, R5)."""
    before = league_shape(reuse.averages, fmt) if reuse is not None else None
    out = []
    for i, (cat, shape) in enumerate(
        zip(fmt.categories, league_shape(comp.averages, fmt), strict=True)
    ):
        mine = next((place for t, place, _, _ in shape["teams"] if t == selected), None)
        marks = {} if mine is None else {mine - 1: "climb", mine: "cushion"}
        prior = before and next(
            (
                {"place": place, "rank": rank, "value": value}
                for t, place, rank, value in before[i]["teams"]
                if t == selected
            ),
            None,
        )
        out.append(
            {
                "category": cat.key,
                "teams": [
                    {
                        "team_id": t,
                        "team_name": names[t],
                        "place": place,
                        "rank": rank,
                        "value": value,
                        "selected": t == selected,
                    }
                    for t, place, rank, value in shape["teams"]
                ],
                "gaps": [
                    {"to_place": r, "gap": g, "null_gap": n, "mark": marks.get(r)}
                    for r, g, n in shape["gaps"]
                ],
                "before": prior or None,
            }
        )
    return out


def _area(radii: list[float]) -> float:
    """Radar polygon area as a fraction of the full polygon (every radius 1).

    With equal angles the area is proportional to the sum of products of adjacent radii, so the
    fraction is sum(r_i * r_(i+1)) / n.
    """
    n = len(radii)
    if n < 3:
        return 0.0
    return float(sum(radii[i] * radii[(i + 1) % n] for i in range(n)) / n)


def _areas(ranks_: list[int], normalized: list[float], win_rate: list[float], teams: int) -> dict:
    """Area for each radar scale, on [0, 1] radii (rank 1 → 1, last place → 0)."""
    span = max(teams - 1, 1)
    rank_radii = [(teams - r) / span for r in ranks_]
    return {"rank": _area(rank_radii), "average": _area(normalized), "win_rate": _area(win_rate)}


def _area_scores(team_ranks: dict, normalized: dict, win_rates: dict) -> dict[int, dict]:
    """Radar area per scale, relative to the league's top team (top team = 1.0)."""
    raw = {
        t: _areas(team_ranks[t], normalized[t], win_rates[t], len(team_ranks)) for t in team_ranks
    }
    out: dict[int, dict] = {t: {} for t in raw}
    for scale in ("rank", "average", "win_rate"):
        top = max(a[scale] for a in raw.values())
        for t, a in raw.items():
            out[t][scale] = a[scale] / top if top > 0 else 0.0
    return out


def _win_rates(values: dict, fmt: ScoringFormat) -> dict[int, list[float]]:
    """Per category, each team's chance of beating a random league opponent.

    For every other team, P(win) + 0.5 * P(tie) over all simulations, averaged across opponents.
    Ties count half, so the league average in every category is exactly 0.5.
    """
    teams = list(values)
    score = {t: np.zeros(len(fmt.categories)) for t in teams}
    for i, a in enumerate(teams):
        for b in teams[i + 1 :]:
            out = fmt.compare(values[a], values[b])
            s = (out > 0).mean(axis=0) + 0.5 * (out == 0).mean(axis=0)
            score[a] += s
            score[b] += 1 - s
    n = max(len(teams) - 1, 1)
    return {t: [float(v / n) for v in s] for t, s in score.items()}


def _radar_league(
    fmt: ScoringFormat, averages: dict, league_avg: np.ndarray, win_rates: dict
) -> list[dict]:
    """The League Average as a radar reference shape (strategic).

    It is placed on each scale as a team with the league's average would be: its competition
    rank, its min-max position, and the league's mean win rate (0.5 by construction).
    """
    keys = {t: fmt.rank_key(a) for t, a in averages.items()}
    avg_key = fmt.rank_key(league_avg)
    avg_ranks, avg_norm = [], []
    for i in range(len(fmt.categories)):
        col = np.array([k[i] for k in keys.values()], dtype=float)
        finite = col[np.isfinite(col)]
        v = avg_key[i]
        avg_ranks.append(1 + int(np.sum(finite > v)) if np.isfinite(v) else len(keys))
        if not np.isfinite(v) or not finite.size:
            avg_norm.append(0.0)
        elif finite.max() == finite.min():
            avg_norm.append(0.5)
        else:
            avg_norm.append(float((v - finite.min()) / (finite.max() - finite.min())))
    n = len(fmt.categories)
    return [
        {
            "role": "league_average",
            "label": "League Average",
            "ranks": avg_ranks,
            "normalized": avg_norm,
            "win_rate": [float(np.mean([w[i] for w in win_rates.values()])) for i in range(n)],
        },
    ]


def _normalized(averages: dict, fmt: ScoringFormat) -> dict[int, list[float]]:
    """Per category, min-max scale every team's projected average to [0, 1] across the league.

    Direction is applied (1 = best, so lower TO is closer to 1). A category where every team
    is equal scales to 0.5; a missing value scales to 0.
    """
    keys = {t: fmt.rank_key(a) for t, a in averages.items()}
    out: dict[int, list[float]] = {t: [] for t in keys}
    for i in range(len(fmt.categories)):
        col = np.array([k[i] for k in keys.values()], dtype=float)
        finite = col[np.isfinite(col)]
        lo, hi = (finite.min(), finite.max()) if finite.size else (0.0, 0.0)
        for t, k in keys.items():
            v = k[i]
            if not np.isfinite(v):
                out[t].append(0.0)
            elif hi == lo:
                out[t].append(0.5)
            else:
                out[t].append(float((v - lo) / (hi - lo)))
    return out


def _favors(diff: float, higher_is_better: bool) -> str:
    if diff is None or not np.isfinite(diff) or diff == 0:
        return "even"
    better = diff > 0 if higher_is_better else diff < 0
    return "selected" if better else "opponent"


def _matchup_warnings(conn, s: AnalysisSettings, scenario, freshness: dict) -> list[dict]:
    """Notices about the matchup state's age (005 FR-017, FR-017a)."""
    out = []
    me, opp = s.team_id, s.opponent_id
    players = scenario.active_players(me) + scenario.active_players(opp)
    if s.as_of > s.matchup_as_of:
        played = count_team_games_bulk(
            conn, players, s.matchup_as_of + timedelta(days=1), s.as_of, statuses=("final",)
        )
        if any(played.values()):
            out.append(
                {
                    "code": "MATCHUP_STALE",
                    "message": f"Games have been played since the matchup was captured"
                    f" ({s.matchup_as_of}), so recent games may be missing.",
                }
            )
    roster_as_of = freshness.get("roster_as_of")
    if roster_as_of and roster_as_of != s.matchup_as_of.isoformat():
        out.append(
            {
                "code": "ROSTER_MATCHUP_DATES_DIFFER",
                "message": f"Rosters are from {roster_as_of} but the matchup is from"
                f" {s.matchup_as_of}, so they may not match.",
            }
        )
    return out


def _tactical_results(
    result,
    s,
    matchup,
    fmt,
    scenario,
    projections,
    values,
    averages,
    team_ranks,
    names,
    teams,
    normalized,
    win_rates,
    area_scores,
    originals,
) -> None:
    """Tactical mode (Constitution IV): the current matchup, week-to-date totals plus the games
    left (005)."""
    me, opp = s.team_id, s.opponent_id
    involved = scenario.active_players(me) + scenario.active_players(opp)
    final = s.matchup_as_of >= s.period_end
    if final or all(projections[p].games_remaining == 0 for p in involved):
        result["warnings"].append(
            {
                "code": "NO_GAMES_REMAINING",
                "message": "No games remain: the matchup result is final.",
            }
        )
    mine_now, theirs_now = matchup.lines[me], matchup.lines[opp]
    now = current_record(mine_now, theirs_now, fmt)
    result["header"]["matchup"] = {
        "opponent_id": opp,
        "opponent_name": names[opp],
        "week": matchup.week,
        "period_start": matchup.period_start,
        "period_end": matchup.period_end,
        "as_of": matchup.as_of,
        "final": final,
        "current": {"wins": now.wins, "losses": now.losses, "ties": now.ties},
    }
    actual_mine, actual_theirs = actual_values(mine_now, fmt), actual_values(theirs_now, fmt)
    odds = matchup_odds(me, values[me], opp, values[opp], fmt)
    if fmt.standings == "category":
        # This week's expected category record: the score so far plus the games left (010 FR-009).
        result["header"]["expected_record"] = _expected(expected_record(odds.categories))
    else:
        rec = record(odds.categories)
        result["header"]["record"] = {
            "wins": rec.wins,
            "losses": rec.losses,
            "ties": rec.ties,
            "unit": "categories",
        }
    result["header"]["matchup_win_probability"] = odds.matchup.win
    # The opponent's roster replaces H2H in tactical mode (005 FR-016).
    result["matchups"] = []
    result["matchup_totals"] = None
    result["radar"] = {
        "team_count": len(teams),
        "series": [
            {
                "team_id": tid,
                "team_name": names[tid],
                "emphasis": emphasis,
                "ranks": team_ranks[tid],
                "normalized": normalized[tid],
                "win_rate": win_rates[tid],
                "area": area_scores[tid],
                "averages": [_num(v) for v in averages[tid]],
            }
            for tid, emphasis in ((opp, "opponent"), (me, "selected"))
        ],
    }
    rows = []
    for i, c in enumerate(fmt.categories):
        mine, theirs = averages[me][i], averages[opp][i]
        diff = mine - theirs
        rows.append(
            {
                "category": c.key,
                "selected_actual": _num(actual_mine[i]),
                "opponent_actual": _num(actual_theirs[i]),
                "selected_average": _num(mine),
                "opponent_average": _num(theirs),
                "difference": _num(diff),
                "favors": _favors(diff, c.higher_is_better),
                "win_probability": odds.categories[i].win,
            }
        )
    result["category_table"] = {"kind": "differences", "rows": rows}
    curves = []
    for i, c in enumerate(fmt.categories):
        roles = {
            "selected": (me, names[me], values[me][:, i], averages[me][i]),
            "opponent": (opp, names[opp], values[opp][:, i], averages[opp][i]),
        }
        for role, (vals, avgs) in originals.items():
            roles[role] = (None, "Original", vals[:, i], avgs[i])
        dens = density_curves({r: v for r, (_, _, v, _) in roles.items()}, seed=s.seed)
        curves.append(
            {
                "category": c.key,
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
    result["curves"] = curves
