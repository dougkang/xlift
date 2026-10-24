"""Write helpers shared by all adapters: idempotent upserts and load_run bookkeeping."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import Engine, text

_CHUNK = 400


@dataclass
class LoadSummary:
    run_id: int
    outcome: str
    inserted: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)
    report: str | None = None
    # Loader-specific facts for the summary (e.g. the matchup week, period and pairings).
    details: dict = field(default_factory=dict)
    replaced: int = 0

    def add(self, table: str, counts: tuple[int, int]) -> None:
        self.inserted[table] = self.inserted.get(table, 0) + counts[0]
        self.updated[table] = self.updated.get(table, 0) + counts[1]

    @property
    def total_inserted(self) -> int:
        return sum(self.inserted.values())

    @property
    def total_updated(self) -> int:
        return sum(self.updated.values())


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, int | float) and isinstance(b, int | float):
        return float(a) == float(b)
    return str(a) == str(b)


def upsert(conn, table: str, key_cols: Sequence[str], rows: Sequence[Mapping]) -> tuple[int, int]:
    """Insert new rows and update changed ones; identical rows are left untouched.

    Returns (inserted, updated). An identical rerun returns (0, 0) (SC-003).
    """
    if not rows:
        return 0, 0
    cols = list(rows[0].keys())
    value_cols = [c for c in cols if c not in key_cols]
    key_list = ", ".join(key_cols)

    existing: dict[tuple, dict] = {}
    for start in range(0, len(rows), _CHUNK):
        chunk = rows[start : start + _CHUNK]
        params, tuples = {}, []
        for i, row in enumerate(chunk):
            names = []
            for k in key_cols:
                params[f"{k}_{i}"] = row[k]
                names.append(f":{k}_{i}")
            tuples.append(f"({', '.join(names)})")
        sql = (
            f"SELECT {', '.join(cols)} FROM {table}"
            f" WHERE ({key_list}) IN (VALUES {', '.join(tuples)})"
        )
        for found in conn.execute(text(sql), params).mappings():
            existing[tuple(found[k] for k in key_cols)] = dict(found)

    to_insert, to_update = [], []
    for row in rows:
        current = existing.get(tuple(row[k] for k in key_cols))
        if current is None:
            to_insert.append(dict(row))
        elif any(not _same(current[c], row[c]) for c in value_cols):
            to_update.append(dict(row))

    if to_insert:
        conn.execute(
            text(
                f"INSERT INTO {table} ({', '.join(cols)})"
                f" VALUES ({', '.join(':' + c for c in cols)})"
            ),
            to_insert,
        )
    if to_update and value_cols:
        conn.execute(
            text(
                f"UPDATE {table} SET {', '.join(f'{c} = :{c}' for c in value_cols)}"
                f" WHERE {' AND '.join(f'{k} = :{k}' for k in key_cols)}"
            ),
            to_update,
        )
    return len(to_insert), len(to_update)


# Exports captured before noon describe the previous day: that day's games are done, and the
# new day's games haven't started (e.g. a 00:07 capture is "as of" the evening before).
AS_OF_CUTOFF_HOUR = 12


def file_date(path: str | Path) -> date:
    """The day an export describes, from its last-modified time in local time (005).

    Modified at or after noon: that date. Before noon: the previous date.
    """
    modified = datetime.fromtimestamp(Path(path).stat().st_mtime)
    day = modified.date()
    return day - timedelta(days=1) if modified.hour < AS_OF_CUTOFF_HOUR else day


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def start_run(engine: Engine, source: str, scope: dict) -> int:
    with engine.begin() as conn:
        return conn.execute(
            text(
                "INSERT INTO load_run (source, scope, started_at, outcome)"
                " VALUES (:s, :scope, :t, 'running') RETURNING run_id"
            ),
            {"s": source, "scope": json.dumps(scope, sort_keys=True), "t": _now()},
        ).scalar_one()


def finish_run(
    engine: Engine,
    run_id: int,
    outcome: str,
    inserted: int = 0,
    updated: int = 0,
    report: str | None = None,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE load_run SET finished_at = :t, outcome = :o, rows_inserted = :i,"
                " rows_updated = :u, report = :r WHERE run_id = :id"
            ),
            {"t": _now(), "o": outcome, "i": inserted, "u": updated, "r": report, "id": run_id},
        )


def ensure_external_id(
    conn,
    table: str,
    source: str,
    external_id: str,
    entity_col: str,
    entity_id: int,
    match_method: str | None = None,
) -> tuple[int, int]:
    row = {"source": source, "external_id": str(external_id), entity_col: entity_id}
    if match_method is not None:
        row["match_method"] = match_method
    return upsert(conn, table, ["source", "external_id"], [row])
