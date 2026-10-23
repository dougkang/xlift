"""Player lookup and accent-insensitive search (FR-023, FR-024)."""

from sqlalchemy import text

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
