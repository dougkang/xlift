"""Matches roster rows to NBA players (research R7, FR-016)."""

import difflib
from collections import defaultdict

from sqlalchemy import text

from ffmodel.adapters.roster_csv.parse import Problem, RosterRow
from ffmodel.contract.names import normalize_name

_POOL_SQL = """
SELECT p.player_id, p.full_name, p.search_name, t.abbreviation AS team
FROM player p LEFT JOIN nba_team t ON t.team_id = p.current_team_id
WHERE p.is_active = 1
   OR p.player_id IN (
        SELECT pg.player_id FROM player_game pg JOIN game g ON g.game_id = pg.game_id
        WHERE g.season_id IN (SELECT season_id FROM season ORDER BY season_id DESC LIMIT 2))
"""


def _initial_key(search_name: str) -> tuple[str, str] | None:
    first, _, rest = search_name.partition(" ")
    return (first[0], rest) if first and rest else None


def match_rows(conn, rows: list[RosterRow], source: str) -> tuple[dict[int, int], list[Problem]]:
    user = dict(
        conn.execute(
            text(
                "SELECT external_id, player_id FROM player_external_id"
                " WHERE source = :s AND match_method = 'user'"
            ),
            {"s": source},
        ).all()
    )
    pool = conn.execute(text(_POOL_SQL)).mappings().all()
    by_name, by_initial = defaultdict(list), defaultdict(list)
    for p in pool:
        by_name[p["search_name"]].append(p)
        key = _initial_key(p["search_name"])
        if key:
            by_initial[key].append(p)

    matches: dict[int, int] = {}
    problems: list[Problem] = []
    for row in rows:
        if row.external_id in user:
            matches[row.line_no] = user[row.external_id]
            continue
        norm = normalize_name(row.name)
        candidates = by_name.get(norm, [])
        if not candidates:
            first = norm.partition(" ")[0]
            key = _initial_key(norm)
            if key and len(first) == 1:
                candidates = by_initial.get(key, [])
        if len(candidates) > 1 and row.nba_team:
            candidates = [c for c in candidates if c["team"] == row.nba_team]
        if len(candidates) == 1:
            matches[row.line_no] = candidates[0]["player_id"]
            continue

        if candidates:
            nearest = candidates[:3]
        else:
            nearest = sorted(
                pool,
                key=lambda p: difflib.SequenceMatcher(None, norm, p["search_name"]).ratio(),
                reverse=True,
            )[:3]
        listed = "  |  ".join(
            f"[{p['player_id']}] {p['full_name']} ({p['team'] or '-'})" for p in nearest
        )
        hint = f"ffm roster resolve --source {source} {row.external_id} <player_id>"
        problems.append(
            Problem(
                "UNRESOLVED",
                f'{source}:{row.external_id}  "{row.name}" ({row.nba_team or "-"})\n'
                f"            candidates: {listed or 'none'}\n            fix: {hint}",
                row.line_no,
            )
        )
    return matches, problems
