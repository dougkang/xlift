"""Database connection for the data contract (Constitution VI)."""

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "backend").is_dir():
            return parent
    return Path.cwd()


def default_db_url() -> str:
    url = os.environ.get("FFMODEL_DB_URL")
    if url:
        return url
    return f"sqlite:///{_repo_root() / 'data' / 'ffmodel.sqlite'}"


def get_engine(url: str | None = None) -> Engine:
    url = url or default_db_url()
    parsed = make_url(url)
    is_sqlite = parsed.get_backend_name() == "sqlite"
    if is_sqlite and parsed.database and parsed.database != ":memory:":
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url)
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.close()

    return engine
