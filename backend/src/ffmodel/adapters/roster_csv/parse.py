"""Parses a roster export (contracts/roster-csv.md)."""

import csv
from dataclasses import dataclass
from pathlib import Path

STATUSES = {"healthy", "DTD", "GTD", "Q", "O", "SUSP", "IL", "IL+", "NA"}
RESERVE_STATUSES = {"IL", "IL+", "NA"}
REQUIRED = ("team_id", "player_id", "name", "team_name", "manager")
COLUMNS = (
    "team_id",
    "player_id",
    "name",
    "positions",
    "nba_team",
    "status",
    "team_name",
    "manager",
)


@dataclass(frozen=True)
class RosterRow:
    line_no: int
    team_key: str
    external_id: str
    name: str
    positions: str | None
    nba_team: str | None
    status: str
    slot: str
    team_name: str
    manager: str


@dataclass(frozen=True)
class Problem:
    kind: str  # MISSING, INCONSISTENT, BAD_STATUS, DUPLICATE, OVER_CAP, UNRESOLVED, NO_SEASON
    message: str
    line_no: int | None = None


def parse_roster_csv(path: str | Path) -> tuple[list[RosterRow], list[Problem]]:
    rows: list[RosterRow] = []
    problems: list[Problem] = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing_cols = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing_cols:
            return [], [Problem("MISSING", f"missing columns: {', '.join(missing_cols)}")]

        teams: dict[str, tuple[str, str, int]] = {}
        for line_no, raw in enumerate(reader, start=2):
            values = {c: (raw.get(c) or "").strip() for c in COLUMNS}
            key = values["team_id"]
            if key and values["team_name"] and values["manager"]:
                seen = teams.setdefault(key, (values["team_name"], values["manager"], line_no))
                if seen[:2] != (values["team_name"], values["manager"]):
                    problems.append(
                        Problem(
                            "INCONSISTENT",
                            f"{key}: team_name/manager"
                            f" {values['team_name']!r}/{values['manager']!r}"
                            f" differs from line {seen[2]} ({seen[0]!r}/{seen[1]!r})",
                            line_no,
                        )
                    )
                    continue

            empty = [c for c in REQUIRED if not values[c]]
            if empty:
                problems.append(Problem("MISSING", f"empty {', '.join(empty)}", line_no))
                continue

            status = values["status"] or "healthy"
            if status not in STATUSES:
                problems.append(Problem("BAD_STATUS", f"unknown status {status!r}", line_no))
                continue

            rows.append(
                RosterRow(
                    line_no=line_no,
                    team_key=key,
                    external_id=values["player_id"],
                    name=values["name"],
                    positions=values["positions"] or None,
                    nba_team=values["nba_team"] or None,
                    status=status,
                    slot="reserve" if status in RESERVE_STATUSES else "active",
                    team_name=values["team_name"],
                    manager=values["manager"],
                )
            )
    return rows, problems
