"""Applies ordered plain-SQL migrations (research R6)."""

import re
from datetime import UTC, datetime
from importlib import resources

from sqlalchemy import Engine, text

_MIGRATION_NAME = re.compile(r"^(\d{4})_(.+)\.sql$")


def _migrations() -> list[tuple[int, str, str]]:
    found = []
    for entry in resources.files("ffmodel.contract.migrations").iterdir():
        match = _MIGRATION_NAME.match(entry.name)
        if match:
            found.append((int(match.group(1)), match.group(2), entry.read_text(encoding="utf-8")))
    return sorted(found)


def _statements(sql: str) -> list[str]:
    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    return [stmt.strip() for stmt in body.split(";") if stmt.strip()]


def _ensure_table(conn) -> None:
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
    )


def current_version(engine: Engine) -> int:
    with engine.begin() as conn:
        _ensure_table(conn)
        return conn.execute(
            text("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
        ).scalar_one()


def migrate(engine: Engine) -> list[int]:
    applied = []
    with engine.begin() as conn:
        _ensure_table(conn)
        done = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}
    for version, name, sql in _migrations():
        if version in done:
            continue
        with engine.begin() as conn:
            for stmt in _statements(sql):
                conn.execute(text(stmt))
            conn.execute(
                text(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (:v, :n, :t)"
                ),
                {"v": version, "n": name, "t": datetime.now(UTC).isoformat()},
            )
        applied.append(version)
    return applied
