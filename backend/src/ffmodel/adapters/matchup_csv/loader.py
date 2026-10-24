"""Loads a matchups export as a league's current matchup state (005, contracts/matchups-csv.md).

All-or-nothing: if any row is invalid, nothing is written and the run is recorded as `rejected`
with a full report. The as-of date and the period default from the file's modified date.
"""

from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import Engine, text

from ffmodel.adapters.common import LoadSummary, file_date, finish_run, start_run
from ffmodel.adapters.matchup_csv.parse import MatchupRow, Problem, parse_matchups_csv

SOURCE = "matchups_csv"

_LABELS = {
    "MISSING": "MISSING",
    "MALFORMED": "MALFORMED",
    "DUPLICATE": "DUPLICATE",
    "BAD_PAIRING": "BAD PAIRING",
    "INCONSISTENT": "INCONSISTENT",
    "BAD_TOTALS": "BAD TOTALS",
    "UNKNOWN_TEAM": "UNKNOWN TEAM",
    "MISSING_TEAM": "MISSING TEAM",
    "NO_LEAGUE": "NO LEAGUE",
    "BAD_PERIOD": "BAD PERIOD",
}


def format_report(problems: list[Problem]) -> str:
    lines = []
    for p in problems:
        where = f"row {p.line_no}  " if p.line_no else ""
        lines.append(f"{_LABELS.get(p.kind, p.kind):<12} {where}{p.message}")
    return "\n".join(lines)


def week_of(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def _team_problems(rows: list[MatchupRow], teams: dict[str, int]) -> list[Problem]:
    problems = []
    seen = {r.team_key for r in rows}
    for r in rows:
        for key in (r.team_key, r.opponent_key):
            if key not in teams:
                problems.append(
                    Problem("UNKNOWN_TEAM", f"{key} is not a team in this league", r.line_no)
                )
    for key in sorted(set(teams) - seen):
        problems.append(Problem("MISSING_TEAM", f"{key} has no row"))
    return problems


def load_matchups(
    engine: Engine,
    path: str | Path,
    league_key: str,
    *,
    as_of: date | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> LoadSummary:
    as_of = as_of or file_date(path)
    default_start, default_end = week_of(as_of)
    start, end = period_start or default_start, period_end or default_end
    scope = {
        "path": str(path),
        "league_key": league_key,
        "as_of": as_of.isoformat(),
        "period": [start.isoformat(), end.isoformat()],
    }
    run_id = start_run(engine, SOURCE, scope)
    summary = LoadSummary(run_id=run_id, outcome="running")
    try:
        rows, problems = parse_matchups_csv(path)
        if end < start:
            problems.append(Problem("BAD_PERIOD", f"period end {end} is before start {start}"))
        with engine.begin() as conn:
            league_id = conn.execute(
                text("SELECT league_id FROM fantasy_league WHERE league_key = :k"),
                {"k": league_key},
            ).scalar_one_or_none()
            if league_id is None:
                problems.append(
                    Problem(
                        "NO_LEAGUE", f"league {league_key} is not loaded; load its roster first"
                    )
                )
                teams, names = {}, {}
            else:
                found = conn.execute(
                    text(
                        "SELECT source_team_key, fantasy_team_id, name FROM fantasy_team"
                        " WHERE league_id = :l"
                    ),
                    {"l": league_id},
                ).all()
                teams = {k: tid for k, tid, _ in found}
                names = {k: n for k, _, n in found}
                problems += _team_problems(rows, teams)
            if not problems:
                _write(conn, summary, league_id, rows, teams, run_id, as_of, start, end)
                summary.details = {
                    "week": rows[0].week,
                    "period": [start.isoformat(), end.isoformat()],
                    "as_of": as_of.isoformat(),
                    "pairings": sorted(
                        {tuple(sorted((names[r.team_key], names[r.opponent_key]))) for r in rows}
                    ),
                }
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


def _write(conn, summary, league_id, rows, teams, run_id, as_of, start, end) -> None:
    """Replace the league's current matchup state in one transaction."""
    replaced = conn.execute(
        text("DELETE FROM matchup_team WHERE league_id = :l"), {"l": league_id}
    ).rowcount
    conn.execute(text("DELETE FROM matchup_state WHERE league_id = :l"), {"l": league_id})
    conn.execute(
        text(
            "INSERT INTO matchup_state (league_id, week, period_start, period_end, as_of, run_id)"
            " VALUES (:l, :w, :s, :e, :a, :r)"
        ),
        {
            "l": league_id,
            "w": rows[0].week,
            "s": start.isoformat(),
            "e": end.isoformat(),
            "a": as_of.isoformat(),
            "r": run_id,
        },
    )
    cols = list(rows[0].totals)
    conn.execute(
        text(
            "INSERT INTO matchup_team (league_id, fantasy_team_id, opponent_team_id, "
            f"{', '.join(cols)}) VALUES (:league_id, :team, :opp, "
            f"{', '.join(':' + c for c in cols)})"
        ),
        [
            {
                "league_id": league_id,
                "team": teams[r.team_key],
                "opp": teams[r.opponent_key],
                **r.totals,
            }
            for r in rows
        ],
    )
    summary.add("matchup_state", (1, 0))
    summary.add("matchup_team", (len(rows), 0))
    if replaced:
        summary.replaced = replaced
