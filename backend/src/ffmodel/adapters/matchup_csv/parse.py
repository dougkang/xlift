"""Parses a matchups export (specs/005-tactical-actuals/contracts/matchups-csv.md)."""

import csv
from dataclasses import dataclass
from pathlib import Path

# File column -> contract column. Other columns (team_name, cat_wins, display %) are ignored.
STATS = {
    "fgm": "fgm",
    "fga": "fga",
    "ftm": "ftm",
    "fta": "fta",
    "tpm": "fg3m",
    "pts": "pts",
    "reb": "reb",
    "ast": "ast",
    "stl": "stl",
    "blk": "blk",
    "to": "tov",
}
REQUIRED = ("week", "team_id", "opponent_id", *STATS)


@dataclass(frozen=True)
class MatchupRow:
    line_no: int
    week: int
    team_key: str
    opponent_key: str
    totals: dict[str, int]  # contract column names


@dataclass(frozen=True)
class Problem:
    # MISSING, MALFORMED, DUPLICATE, BAD_PAIRING, INCONSISTENT, BAD_TOTALS,
    # UNKNOWN_TEAM, MISSING_TEAM (the last two are found by the loader)
    kind: str
    message: str
    line_no: int | None = None


def _totals_problems(row: MatchupRow) -> list[str]:
    t = row.totals
    bad = []
    if t["fgm"] > t["fga"]:
        bad.append(f"fgm {t['fgm']} > fga {t['fga']}")
    if t["ftm"] > t["fta"]:
        bad.append(f"ftm {t['ftm']} > fta {t['fta']}")
    if t["fg3m"] > t["fgm"]:
        bad.append(f"tpm {t['fg3m']} > fgm {t['fgm']}")
    expected = 2 * t["fgm"] + t["fg3m"] + t["ftm"]
    if t["pts"] != expected:
        bad.append(f"pts {t['pts']} != 2·fgm + tpm + ftm = {expected}")
    return bad


def parse_matchups_csv(path: str | Path) -> tuple[list[MatchupRow], list[Problem]]:
    rows: list[MatchupRow] = []
    problems: list[Problem] = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            return [], [Problem("MISSING", f"missing columns: {', '.join(missing)}")]
        for line_no, raw in enumerate(reader, start=2):
            values = {c: (raw.get(c) or "").strip() for c in REQUIRED}
            numbers = {}
            for col in ("week", *STATS):
                v = values[col]
                if not v.isdigit():
                    problems.append(
                        Problem("MALFORMED", f"{col} {v!r} is not a whole number", line_no)
                    )
                else:
                    numbers[col] = int(v)
            if not values["team_id"] or not values["opponent_id"]:
                problems.append(Problem("MISSING", "team_id and opponent_id are required", line_no))
                continue
            if len(numbers) < 1 + len(STATS):
                continue
            row = MatchupRow(
                line_no=line_no,
                week=numbers["week"],
                team_key=values["team_id"],
                opponent_key=values["opponent_id"],
                totals={STATS[c]: numbers[c] for c in STATS},
            )
            for msg in _totals_problems(row):
                problems.append(Problem("BAD_TOTALS", f"{row.team_key}: {msg}", line_no))
            rows.append(row)

    problems += _file_problems(rows)
    return rows, problems


def _file_problems(rows: list[MatchupRow]) -> list[Problem]:
    problems = []
    weeks = sorted({r.week for r in rows})
    if len(weeks) > 1:
        problems.append(Problem("INCONSISTENT", f"rows cover several weeks: {weeks}"))
    by_team: dict[str, MatchupRow] = {}
    for r in rows:
        if r.team_key in by_team:
            problems.append(
                Problem(
                    "DUPLICATE",
                    f"{r.team_key} appears on rows {by_team[r.team_key].line_no} and {r.line_no}",
                    r.line_no,
                )
            )
        else:
            by_team[r.team_key] = r
    for r in by_team.values():
        if r.opponent_key == r.team_key:
            problems.append(Problem("BAD_PAIRING", f"{r.team_key} plays itself", r.line_no))
            continue
        other = by_team.get(r.opponent_key)
        if other is not None and other.opponent_key != r.team_key:
            problems.append(
                Problem(
                    "BAD_PAIRING",
                    f"{r.team_key} plays {r.opponent_key}, but {r.opponent_key}"
                    f" plays {other.opponent_key}",
                    r.line_no,
                )
            )
    return problems
