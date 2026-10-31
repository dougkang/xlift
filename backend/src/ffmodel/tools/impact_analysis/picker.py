"""Player picker: everyone not on the selected team, with move eligibility (FR-020, FR-026).

Eligibility is computed here from the scenario so the frontend never applies roster rules.
Rows are ranked by xLift for the selected team, then paged (007 research R7). Position and owner
filters and the category sort (013) are applied here too, so pages stay right.
"""

from collections.abc import Sequence

from ffmodel.contract.names import name_words
from ffmodel.core.data import (
    count_team_games_bulk,
    get_last_n_games_bulk,
    get_matchup_state,
    get_player_details,
)
from ffmodel.core.scoring import UnsupportedFormat, get_format
from ffmodel.core.value import score_pool_by_category
from ffmodel.tools.impact_analysis import cache, fragility, value
from ffmodel.tools.impact_analysis.settings import AnalysisSettings, normalize
from ffmodel.tools.impact_analysis.state import load_state

FOOTNOTE_MARKER = "*"
FREE_AGENTS = "fa"  # the owners filter's value for free agents (013)


class InvalidQuery(ValueError):
    """A picker query the league's format can't answer, e.g. an unknown category (422)."""


def _eligibility(scenario, team_id: int, owner_team: int | None, owner_name: str | None) -> dict:
    open_slots = scenario.open_active_slots(team_id)
    if owner_team is None:
        return {
            "can_add": open_slots > 0,
            "add_blocked_reason": None
            if open_slots
            else "No open active slot — drop a player first",
            "swap_give_options": [],
        }
    options = []
    if scenario.rosters[team_id]:
        options.append("roster")
    if open_slots:
        options.append("free_agent")
    return {
        "can_add": False,
        "add_blocked_reason": f"On {owner_name}: swap required",
        "swap_give_options": options,
    }


def list_players(
    conn,
    settings: AnalysisSettings,
    moves: Sequence = (),
    *,
    query: str = "",
    limit: int = 50,
    offset: int = 0,
    free_agents_only: bool = False,
    positions: Sequence[str] = (),
    owners: Sequence[str | int] = (),
    sort_categories: Sequence[str] = (),
) -> dict:
    """`positions`, `owners` (team ids or "fa") and `sort_categories` (category keys) are empty for
    no filter and total-xLift order (013)."""
    s = normalize(
        settings,
        get_matchup_state(conn, settings.league_id) if settings.mode == "tactical" else None,
    )
    state = load_state(conn, s.league_id, s.team_id, moves)
    scenario, names = state.scenario, state.names
    owner = scenario.owner

    pool = get_player_details(conn, league_id=s.league_id) | state.info
    words = name_words(query)
    candidates = []
    for pid, (summary, status) in pool.items():
        team = owner.get(pid)
        if team == s.team_id or (free_agents_only and team is not None):
            continue
        if team is None and not summary.is_active:
            continue
        search = " ".join(name_words(summary.full_name))
        if words and not all(w in search for w in words):
            continue
        if positions and not set(positions) & set(summary.positions):
            continue
        if owners and (FREE_AGENTS if team is None else team) not in owners:
            continue
        candidates.append((pid, summary, status, team))

    statuses = {pid: status for pid, (_, status) in pool.items()}
    xlift, projections = _score(conn, s, state, [c[0] for c in candidates], statuses)
    # Ranked by total xLift, or by the xLift summed over the picked categories (013).
    sort_xlift = (
        _category_sums(conn, s, state, [c[0] for c in candidates], statuses, sort_categories)
        if sort_categories
        else {}
    )
    rank = sort_xlift if sort_categories else xlift
    # Free agents first; within each group, highest first, then name; unscored last.
    candidates.sort(
        key=lambda c: (
            c[3] is not None,
            rank.get(c[0]) is None,
            -(rank.get(c[0]) or 0.0),
            c[1].full_name,
            c[0],
        )
    )
    page = candidates[offset : offset + limit]

    ids = [c[0] for c in page]
    remaining = (
        count_team_games_bulk(conn, ids, *s.remaining, statuses=("scheduled", "final"))
        if s.remaining
        else {}
    )
    if not projections:  # unsupported format: nothing projected, so read the windows directly
        windows = get_last_n_games_bulk(conn, ids, s.window, as_of=s.as_of)
        projections = {pid: (w.found, w.requested) for pid, w in windows.items()}
    rows = []
    for pid, summary, status, team in page:
        found, requested = _games(pid, projections)
        short = found < requested
        rows.append(
            {
                "player_id": pid,
                "name": summary.full_name,
                "nba_team": summary.current_team,
                "positions": list(summary.positions),
                "owner_team_id": team,
                "owner_label": names[team] if team is not None else "FA",
                "status": status,
                "games_found": found,
                "games_requested": requested,
                "games_remaining": remaining.get(pid, 0) if s.mode == "tactical" else None,
                "footnote": f"{FOOTNOTE_MARKER} {found} of {requested} games" if short else None,
                "xlift": xlift.get(pid),
                "sort_xlift": sort_xlift.get(pid),
                "eligibility": _eligibility(scenario, s.team_id, team, names.get(team)),
            }
        )
    return {"total": len(candidates), "players": rows}


def _score(conn, s, state, ids: list[int], statuses: dict) -> tuple[dict, dict]:
    """({player: xLift for the selected team}, their projections); empty for an unsupported
    format."""
    try:
        fmt = get_format(state.scenario.league.scoring_format_id)
    except UnsupportedFormat:
        return {}, {}
    scenario = state.scenario
    rostered = [spot.player_id for spots in scenario.rosters.values() for spot in spots]

    def penalize(proj, sc):  # the Fragility Penalty (007 FR-013)
        return fragility.apply(s.fragility, proj, sc, statuses, conn, s.as_of)

    projections = penalize(cache.projections(conn, set(ids) | set(rostered), fmt, s), scenario)
    spread = value.league_spread(conn, fmt, s, state.snapshot, penalize)
    pool = {pid: projections[pid] for pid in ids}
    roster = {pid: projections[pid] for pid in rostered}
    scores = value.score_pool(scenario, s.team_id, pool, fmt, s.games_per_period, spread, roster)
    return scores, projections


def _category_sums(conn, s, state, ids, statuses, keys: Sequence[str]) -> dict:
    """{player: xLift summed over the categories `keys`} for the selected team, from the same
    per-category breakdown as Player Analysis (009 FR-007); empty for an unsupported format."""
    try:
        fmt = get_format(state.scenario.league.scoring_format_id)
    except UnsupportedFormat:
        return {}
    known = [c.key for c in fmt.categories]
    unknown = [k for k in keys if k not in known]
    if unknown:
        raise InvalidQuery(f"unknown categories: {', '.join(unknown)}")
    picked = [known.index(k) for k in dict.fromkeys(keys)]
    scenario = state.scenario
    rostered = [spot.player_id for spots in scenario.rosters.values() for spot in spots]

    def penalize(proj, sc):
        return fragility.apply(s.fragility, proj, sc, statuses, conn, s.as_of)

    projections = penalize(cache.projections(conn, set(ids) | set(rostered), fmt, s), scenario)
    spread = value.league_spread(conn, fmt, s, state.snapshot, penalize)
    by_cat = score_pool_by_category(
        scenario,
        s.team_id,
        {pid: projections[pid] for pid in ids},
        fmt,
        s.games_per_period,
        spread,
        {pid: projections[pid] for pid in rostered},
    )
    return {pid: float(v[picked].sum()) for pid, v in by_cat.items() if v is not None}


def _games(pid: int, projections: dict) -> tuple[int, int]:
    p = projections[pid]
    return p if isinstance(p, tuple) else (p.games_found, p.games_requested)
