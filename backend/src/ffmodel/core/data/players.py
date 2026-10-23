"""Player lookup and accent-insensitive search (FR-023, FR-024)."""

from sqlalchemy import bindparam, text

from ffmodel.contract.names import name_words
from ffmodel.core.data._rows import PLAYER_COLUMNS, PLAYER_FROM, player_summary
from ffmodel.core.data.models import PlayerSummary


def search_players(
    conn, query: str, *, active_only: bool = False, limit: int = 25
) -> list[PlayerSummary]:
    words = name_words(query)
    if not words:
        return []
    params: dict = {f"w{i}": w for i, w in enumerate(words)}
    params |= {"prefix": words[0] + "%", "limit": limit}
    clauses = [f"p.search_name LIKE '%' || :w{i} || '%'" for i in range(len(words))]
    if active_only:
        clauses.append("p.is_active = 1")
    rows = conn.execute(
        text(
            f"SELECT {PLAYER_COLUMNS} FROM {PLAYER_FROM} WHERE {' AND '.join(clauses)}"
            " ORDER BY CASE WHEN p.search_name LIKE :prefix THEN 0 ELSE 1 END, p.full_name,"
            " p.player_id LIMIT :limit"
        ),
        params,
    ).mappings()
    return [player_summary(r) for r in rows]


def get_player(conn, player_id: int) -> PlayerSummary | None:
    row = (
        conn.execute(
            text(f"SELECT {PLAYER_COLUMNS} FROM {PLAYER_FROM} WHERE p.player_id = :p"),
            {"p": player_id},
        )
        .mappings()
        .one_or_none()
    )
    return player_summary(row) if row else None


_STATUS = (
    "(SELECT s.status FROM player_status s WHERE s.player_id = p.player_id"
    " ORDER BY s.as_of DESC, s.source LIMIT 1)"
)


def get_player_details(
    conn, *, league_id: int | None = None, player_ids=None
) -> dict[int, tuple[PlayerSummary, str]]:
    """Players with their latest status ("healthy" if none).

    With `league_id`: every active player plus everyone rostered in that league (the picker
    pool). With `player_ids`: exactly those players. Both may be combined.
    """
    clauses, params = [], {}
    if league_id is not None:
        clauses.append(
            "p.is_active = 1 OR p.player_id IN"
            " (SELECT player_id FROM roster_entry WHERE league_id = :league)"
        )
        params["league"] = league_id
    stmt_ids = list(player_ids or [])
    if stmt_ids:
        clauses.append("p.player_id IN :ids")
        params["ids"] = stmt_ids
    if not clauses:
        return {}
    stmt = text(
        f"SELECT {PLAYER_COLUMNS}, {_STATUS} AS status FROM {PLAYER_FROM}"
        f" WHERE {' OR '.join(f'({c})' for c in clauses)}"
    )
    if stmt_ids:
        stmt = stmt.bindparams(bindparam("ids", expanding=True))
    return {
        r["player_id"]: (player_summary(r), r["status"] or "healthy")
        for r in conn.execute(stmt, params).mappings()
    }
