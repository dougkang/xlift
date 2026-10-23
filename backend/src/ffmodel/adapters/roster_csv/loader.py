"""Loads a roster export into one fantasy league (FR-014 – FR-019).

All-or-nothing: if any row is invalid or unresolved, nothing is written and the run is
recorded as `rejected` with a full report.
"""

from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import Engine, text

from ffmodel.adapters.common import LoadSummary, finish_run, start_run, upsert
from ffmodel.adapters.roster_csv.match import match_rows
from ffmodel.adapters.roster_csv.parse import Problem, RosterRow, parse_roster_csv
from ffmodel.contract.seasons import current_season

SOURCE = "roster_csv"
DEFAULT_FORMAT = "9cat_h2h"
DEFAULT_CAPACITY = 10

_LABELS = {
    "UNRESOLVED": "UNRESOLVED",
    "OVER_CAP": "OVER CAP",
    "DUPLICATE": "DUPLICATE",
    "MISSING": "MISSING",
    "INCONSISTENT": "INCONSISTENT",
    "BAD_STATUS": "BAD STATUS",
    "NO_SEASON": "NO SEASON",
}


def format_report(problems: list[Problem]) -> str:
    lines = []
    for p in problems:
        where = f"row {p.line_no}  " if p.line_no else ""
        lines.append(f"{_LABELS.get(p.kind, p.kind):<11} {where}{p.message}")
    return "\n".join(lines)


def _validate(rows: list[RosterRow], matches: dict[int, int], capacity: int) -> list[Problem]:
    problems = []
    by_player = defaultdict(list)
    for row in rows:
        if row.line_no in matches:
            by_player[matches[row.line_no]].append(row)
    for player_rows in by_player.values():
        if len(player_rows) > 1:
            where = " and ".join(f"{r.team_key} (row {r.line_no})" for r in player_rows)
            problems.append(Problem("DUPLICATE", f"{player_rows[0].external_id} on {where}"))
    active = Counter(r.team_key for r in rows if r.slot == "active")
    names = {r.team_key: r.team_name for r in rows}
    for team, n in sorted(active.items()):
        if n > capacity:
            problems.append(
                Problem("OVER_CAP", f'{team} "{names[team]}": {n} active > capacity {capacity}')
            )
    return problems


def _league(conn, league_key: str) -> dict | None:
    row = (
        conn.execute(text("SELECT * FROM fantasy_league WHERE league_key = :k"), {"k": league_key})
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


def _id_map(conn, sql: str, params: dict) -> dict:
    return dict(conn.execute(text(sql), params).all())


def _write(conn, summary: LoadSummary, rows, matches, settings: dict, source: str, as_of: str):
    existing = _league(conn, settings["league_key"])
    if existing is None:
        league_id = conn.execute(
            text(
                "INSERT INTO fantasy_league (league_key, name, season_id, scoring_format_id,"
                " active_roster_capacity) VALUES (:league_key, :name, :season_id,"
                " :scoring_format_id, :active_roster_capacity) RETURNING league_id"
            ),
            settings,
        ).scalar_one()
        summary.add("fantasy_league", (1, 0))
    else:
        league_id = existing["league_id"]
        summary.add(
            "fantasy_league",
            upsert(conn, "fantasy_league", ["league_id"], [{"league_id": league_id, **settings}]),
        )

    managers = sorted({r.manager for r in rows})
    known = _id_map(
        conn, "SELECT display_name, manager_id FROM manager WHERE league_id = :l", {"l": league_id}
    )
    for name in managers:
        if name not in known:
            known[name] = conn.execute(
                text(
                    "INSERT INTO manager (league_id, display_name) VALUES (:l, :n)"
                    " RETURNING manager_id"
                ),
                {"l": league_id, "n": name},
            ).scalar_one()
            summary.add("manager", (1, 0))

    teams = {r.team_key: (r.team_name, known[r.manager]) for r in rows}
    team_ids = _id_map(
        conn,
        "SELECT source_team_key, fantasy_team_id FROM fantasy_team WHERE league_id = :l",
        {"l": league_id},
    )
    updates = []
    for key, (name, manager_id) in sorted(teams.items()):
        if key in team_ids:
            updates.append(
                {"fantasy_team_id": team_ids[key], "name": name, "manager_id": manager_id}
            )
        else:
            team_ids[key] = conn.execute(
                text(
                    "INSERT INTO fantasy_team (league_id, source_team_key, name, manager_id)"
                    " VALUES (:l, :k, :n, :m) RETURNING fantasy_team_id"
                ),
                {"l": league_id, "k": key, "n": name, "m": manager_id},
            ).scalar_one()
            summary.add("fantasy_team", (1, 0))
    summary.add("fantasy_team", upsert(conn, "fantasy_team", ["fantasy_team_id"], updates))

    entries = [
        {
            "league_id": league_id,
            "player_id": matches[r.line_no],
            "fantasy_team_id": team_ids[r.team_key],
            "slot": r.slot,
            "source_positions": r.positions,
        }
        for r in rows
    ]
    keep = {e["player_id"] for e in entries}
    current = {
        pid
        for (pid,) in conn.execute(
            text("SELECT player_id FROM roster_entry WHERE league_id = :l"), {"l": league_id}
        )
    }
    for pid in current - keep:
        conn.execute(
            text("DELETE FROM roster_entry WHERE league_id = :l AND player_id = :p"),
            {"l": league_id, "p": pid},
        )
    summary.add("roster_entry", (0, len(current - keep)))
    summary.add("roster_entry", upsert(conn, "roster_entry", ["league_id", "player_id"], entries))

    gone_teams = [tid for key, tid in team_ids.items() if key not in teams]
    for tid in gone_teams:
        conn.execute(text("DELETE FROM fantasy_team WHERE fantasy_team_id = :t"), {"t": tid})
    conn.execute(
        text(
            "DELETE FROM manager WHERE league_id = :l AND manager_id NOT IN"
            " (SELECT manager_id FROM fantasy_team WHERE league_id = :l)"
        ),
        {"l": league_id},
    )

    summary.add(
        "player_status",
        upsert(
            conn,
            "player_status",
            ["player_id", "source", "as_of"],
            [
                {
                    "player_id": matches[r.line_no],
                    "source": source,
                    "as_of": as_of,
                    "status": r.status,
                }
                for r in rows
            ],
        ),
    )

    user = {
        ext
        for (ext,) in conn.execute(
            text(
                "SELECT external_id FROM player_external_id WHERE source = :s"
                " AND match_method = 'user'"
            ),
            {"s": source},
        )
    }
    summary.add(
        "player_external_id",
        upsert(
            conn,
            "player_external_id",
            ["source", "external_id"],
            [
                {
                    "source": source,
                    "external_id": r.external_id,
                    "player_id": matches[r.line_no],
                    "match_method": "auto",
                }
                for r in rows
                if r.external_id not in user
            ],
        ),
    )


def load_roster(
    engine: Engine,
    path: str | Path,
    league_key: str,
    name: str | None = None,
    season: str | None = None,
    scoring_format: str | None = None,
    capacity: int | None = None,
    source: str = "yahoo",
    as_of: date | None = None,
) -> LoadSummary:
    as_of = as_of or date.today()
    season = season or current_season(as_of)
    scope = {
        "path": str(path),
        "league_key": league_key,
        "season": season,
        "source": source,
        "as_of": as_of.isoformat(),
    }
    run_id = start_run(engine, SOURCE, scope)
    summary = LoadSummary(run_id=run_id, outcome="running")
    try:
        rows, problems = parse_roster_csv(path)
        with engine.begin() as conn:
            existing = _league(conn, league_key)
            if not conn.execute(
                text("SELECT 1 FROM season WHERE season_id = :s"), {"s": season}
            ).first():
                problems.append(
                    Problem("NO_SEASON", f"season {season} is not loaded; run `ffm load nba` first")
                )
            settings = {
                "league_key": league_key,
                "name": name or (existing["name"] if existing else league_key),
                "season_id": season,
                "scoring_format_id": scoring_format
                or (existing["scoring_format_id"] if existing else DEFAULT_FORMAT),
                "active_roster_capacity": capacity
                or (existing["active_roster_capacity"] if existing else DEFAULT_CAPACITY),
            }
            matches, unresolved = match_rows(conn, rows, source)
            problems += unresolved
            problems += _validate(rows, matches, settings["active_roster_capacity"])
            if not problems:
                _write(conn, summary, rows, matches, settings, source, as_of.isoformat())
    except Exception as exc:
        summary.outcome, summary.report = "failed", f"{type(exc).__name__}: {exc}"
        finish_run(engine, run_id, "failed", report=summary.report)
        raise

    if problems:
        summary.outcome, summary.report = "rejected", format_report(problems)
        finish_run(engine, run_id, "rejected", report=summary.report)
        return summary
    summary.outcome = "succeeded"
    finish_run(engine, run_id, "succeeded", summary.total_inserted, summary.total_updated)
    return summary


def resolve_match(engine: Engine, source: str, external_id: str, player_id: int) -> None:
    """Record a user-confirmed match; it wins over automatic matching on later loads."""
    with engine.begin() as conn:
        if not conn.execute(
            text("SELECT 1 FROM player WHERE player_id = :p"), {"p": player_id}
        ).first():
            raise ValueError(f"no player with player_id {player_id}")
        upsert(
            conn,
            "player_external_id",
            ["source", "external_id"],
            [
                {
                    "source": source,
                    "external_id": external_id,
                    "player_id": player_id,
                    "match_method": "user",
                }
            ],
        )
