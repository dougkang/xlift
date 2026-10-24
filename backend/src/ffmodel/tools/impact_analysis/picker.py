"""Player picker: everyone not on the selected team, with move eligibility (FR-020, FR-026).

Eligibility is computed here from the scenario so the frontend never applies roster rules.
"""

from collections.abc import Sequence

from ffmodel.contract.names import name_words
from ffmodel.core.data import (
    count_team_games_bulk,
    get_last_n_games_bulk,
    get_matchup_state,
    get_player_details,
)
from ffmodel.tools.impact_analysis.settings import AnalysisSettings, normalize
from ffmodel.tools.impact_analysis.state import load_state

FOOTNOTE_MARKER = "*"


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
) -> dict:
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
        candidates.append((team is not None, summary.full_name, pid, summary, status, team))
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    page = candidates[offset : offset + limit]

    ids = [c[2] for c in page]
    windows = get_last_n_games_bulk(conn, ids, s.window, as_of=s.as_of)
    remaining = (
        count_team_games_bulk(conn, ids, *s.remaining, statuses=("scheduled", "final"))
        if s.remaining
        else {}
    )
    rows = []
    for _, _, pid, summary, status, team in page:
        w = windows[pid]
        short = w.found < w.requested
        rows.append(
            {
                "player_id": pid,
                "name": summary.full_name,
                "nba_team": summary.current_team,
                "positions": list(summary.positions),
                "owner_team_id": team,
                "owner_label": names[team] if team is not None else "FA",
                "status": status,
                "games_found": w.found,
                "games_requested": w.requested,
                "games_remaining": remaining.get(pid, 0) if s.mode == "tactical" else None,
                "footnote": f"{FOOTNOTE_MARKER} {w.found} of {w.requested} games"
                if short
                else None,
                "eligibility": _eligibility(scenario, s.team_id, team, names.get(team)),
            }
        )
    return {"total": len(candidates), "players": rows}
