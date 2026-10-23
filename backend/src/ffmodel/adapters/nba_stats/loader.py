"""Fills the NBA side of the data contract from nba_api (FR-006 – FR-013).

Regular season only (FR-012). Every write is an idempotent upsert, and each game's box scores
are written in one transaction (FR-008).
"""

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import Engine, bindparam, text

from ffmodel.adapters.common import LoadSummary, finish_run, start_run, upsert
from ffmodel.adapters.nba_stats.client import NbaStatsClient
from ffmodel.adapters.nba_stats.mapping import (
    box_score_row,
    current_season,
    normalize_positions,
    previous_season,
    schedule_game_row,
    season_type_from_game_id,
)
from ffmodel.adapters.nba_stats.stints import derive_stints
from ffmodel.contract.names import normalize_name

SOURCE = "nba_stats"
OVERLAP_DAYS = 3


def _external_map(conn, table: str, entity_col: str) -> dict[str, int]:
    rows = conn.execute(
        text(f"SELECT external_id, {entity_col} FROM {table} WHERE source = :s"), {"s": SOURCE}
    )
    return {ext: eid for ext, eid in rows}


def _ensure(
    conn,
    summary: LoadSummary,
    table: str,
    id_col: str,
    ext_table: str,
    records: dict[str, dict],
    update: bool = True,
    match_method: str | None = None,
) -> dict[str, int]:
    """Insert entities new to this source, update known ones; return external -> internal id."""
    ids = _external_map(conn, ext_table, id_col)
    updates = []
    for ext, row in records.items():
        if ext in ids:
            if update:
                updates.append({id_col: ids[ext], **row})
            continue
        cols = list(row)
        new_id = conn.execute(
            text(
                f"INSERT INTO {table} ({', '.join(cols)})"
                f" VALUES ({', '.join(':' + c for c in cols)})"
                f" RETURNING {id_col}"
            ),
            row,
        ).scalar_one()
        ext_row = {"source": SOURCE, "external_id": ext, id_col: new_id}
        if match_method:
            ext_row["match_method"] = match_method
        conn.execute(
            text(
                f"INSERT INTO {ext_table} ({', '.join(ext_row)})"
                f" VALUES ({', '.join(':' + c for c in ext_row)})"
            ),
            ext_row,
        )
        ids[ext] = new_id
        summary.add(table, (1, 0))
    if updates:
        summary.add(table, upsert(conn, table, [id_col], updates))
    return ids


def _load_teams(conn, summary: LoadSummary) -> dict[str, int]:
    from nba_api.stats.static import teams

    records = {
        str(t["id"]): {"abbreviation": t["abbreviation"], "city": t["city"], "name": t["nickname"]}
        for t in teams.get_teams()
    }
    return _ensure(conn, summary, "nba_team", "team_id", "nba_team_external_id", records)


def _player_record(first: str, last: str, positions, team_id, is_active: int) -> dict:
    full = f"{first} {last}".strip()
    return {
        "full_name": full,
        "first_name": first or None,
        "last_name": last or None,
        "search_name": normalize_name(full),
        "positions": positions,
        "current_team_id": team_id,
        "is_active": is_active,
    }


def _load_players(
    conn, summary: LoadSummary, index: list[dict], team_ids: dict[str, int], is_current: bool
) -> dict[str, int]:
    records = {
        str(p["PERSON_ID"]): _player_record(
            p["PLAYER_FIRST_NAME"] or "",
            p["PLAYER_LAST_NAME"] or "",
            normalize_positions(p.get("POSITION")),
            team_ids.get(str(p["TEAM_ID"])) if is_current else None,
            1 if is_current else 0,
        )
        for p in index
    }
    ids = _ensure(
        conn,
        summary,
        "player",
        "player_id",
        "player_external_id",
        records,
        update=is_current,
        match_method="exact",
    )
    if is_current:
        current = [ids[ext] for ext in records]
        stmt = text(
            "UPDATE player SET is_active = 0, current_team_id = NULL"
            " WHERE player_id NOT IN :ids AND (is_active = 1 OR current_team_id IS NOT NULL)"
        ).bindparams(bindparam("ids", expanding=True))
        changed = conn.execute(stmt, {"ids": current or [-1]}).rowcount
        summary.add("player", (0, changed))
    return ids


def _load_schedule(
    conn, summary: LoadSummary, season: str, schedule: list[dict], team_ids: dict[str, int]
) -> dict[str, int]:
    records = {}
    for g in schedule:
        try:
            if season_type_from_game_id(g["gameId"]) != "regular":
                continue
        except ValueError:
            continue
        home, away = (
            team_ids.get(str(g["homeTeam_teamId"])),
            team_ids.get(str(g["awayTeam_teamId"])),
        )
        if home is None or away is None:
            continue
        records[str(g["gameId"])] = schedule_game_row(g, season, home, away)
    if records:
        dates = sorted(r["game_date"] for r in records.values())
        summary.add(
            "season",
            upsert(
                conn,
                "season",
                ["season_id"],
                [{"season_id": season, "start_date": dates[0], "end_date": dates[-1]}],
            ),
        )
    return _ensure(conn, summary, "game", "game_id", "game_external_id", records)


def _box_cursor(conn, season: str) -> str | None:
    latest = conn.execute(
        text(
            "SELECT MAX(g.game_date) FROM game g WHERE g.season_id = :s"
            " AND EXISTS (SELECT 1 FROM player_game pg WHERE pg.game_id = g.game_id)"
        ),
        {"s": season},
    ).scalar_one()
    if latest is None:
        return None
    return (date.fromisoformat(latest) - timedelta(days=OVERLAP_DAYS)).isoformat()


def _load_box_scores(
    engine: Engine,
    summary: LoadSummary,
    client,
    season: str,
    full: bool,
    team_ids: dict[str, int],
    game_ids: dict[str, int],
) -> None:
    with engine.connect() as conn:
        date_from = None if full else _box_cursor(conn, season)
    log = client.game_log(season, date_from)
    by_game: dict[str, list[dict]] = defaultdict(list)
    for row in log:
        by_game[str(row["GAME_ID"])].append(row)

    for ext_game, rows in sorted(by_game.items()):
        game_id = game_ids.get(ext_game)
        if game_id is None:
            continue
        with engine.begin() as conn:
            # A game with box scores is final, even if the schedule snapshot was older.
            summary.add(
                "game", upsert(conn, "game", ["game_id"], [{"game_id": game_id, "status": "final"}])
            )
            player_ids = _external_map(conn, "player_external_id", "player_id")
            box_rows = []
            for r in rows:
                ext_player = str(r["PLAYER_ID"])
                if ext_player not in player_ids:
                    first, _, last = (r.get("PLAYER_NAME") or "").partition(" ")
                    player_ids |= _ensure(
                        conn,
                        summary,
                        "player",
                        "player_id",
                        "player_external_id",
                        {ext_player: _player_record(first, last, None, None, 0)},
                        update=False,
                        match_method="exact",
                    )
                team_id = team_ids[str(r["TEAM_ID"])]
                box_rows.append(box_score_row(r, game_id, player_ids[ext_player], team_id))
            summary.add(
                "player_game", upsert(conn, "player_game", ["game_id", "player_id"], box_rows)
            )


def _recompute_stints(
    conn, summary: LoadSummary, season: str, is_current: bool, index_player_ids: set[int]
) -> None:
    bounds = conn.execute(
        text("SELECT start_date, end_date FROM season WHERE season_id = :s"), {"s": season}
    ).one_or_none()
    if bounds is None:
        return
    season_start, season_end = (date.fromisoformat(b) for b in bounds)

    appearances: dict[int, list[tuple[date, int]]] = defaultdict(list)
    for pid, day, team in conn.execute(
        text(
            "SELECT pg.player_id, g.game_date, pg.team_id FROM player_game pg"
            " JOIN game g ON g.game_id = pg.game_id"
            " WHERE g.season_id = :s AND g.season_type = 'regular'"
        ),
        {"s": season},
    ):
        appearances[pid].append((date.fromisoformat(day), team))

    players = set(appearances) | (index_player_ids if is_current else set())
    current_team = (
        dict(conn.execute(text("SELECT player_id, current_team_id FROM player")).all())
        if is_current
        else {}
    )

    for pid in sorted(players):
        stints = derive_stints(
            appearances.get(pid, []),
            season_start,
            current_team_id=current_team.get(pid) if is_current else None,
            season_end=None if is_current else season_end,
        )
        rows = [
            {
                "player_id": pid,
                "start_date": s.start_date.isoformat(),
                "team_id": s.team_id,
                "end_date": s.end_date.isoformat() if s.end_date else None,
            }
            for s in stints
        ]
        keep = {r["start_date"] for r in rows}
        stale = [
            start
            for (start,) in conn.execute(
                text(
                    "SELECT start_date FROM player_team_stint WHERE player_id = :p"
                    " AND start_date BETWEEN :a AND :b"
                ),
                {"p": pid, "a": season_start.isoformat(), "b": season_end.isoformat()},
            )
            if start not in keep
        ]
        for start in stale:
            conn.execute(
                text("DELETE FROM player_team_stint WHERE player_id = :p AND start_date = :s"),
                {"p": pid, "s": start},
            )
        summary.add("player_team_stint", (0, len(stale)))
        summary.add(
            "player_team_stint",
            upsert(conn, "player_team_stint", ["player_id", "start_date"], rows),
        )


def load_nba(
    engine: Engine,
    seasons: list[str] | None = None,
    full: bool = False,
    client: NbaStatsClient | None = None,
    today: date | None = None,
) -> LoadSummary:
    today = today or date.today()
    current = current_season(today)
    seasons = sorted(set(seasons or [previous_season(current), current]))
    client = client or NbaStatsClient()

    run_id = start_run(engine, SOURCE, {"seasons": seasons, "incremental": not full})
    summary = LoadSummary(run_id=run_id, outcome="running")
    try:
        with engine.begin() as conn:
            team_ids = _load_teams(conn, summary)
        for season in seasons:
            is_current = season == current
            schedule = client.schedule(season)
            index = client.player_index(season)
            with engine.begin() as conn:
                game_ids = _load_schedule(conn, summary, season, schedule, team_ids)
                player_ids = _load_players(conn, summary, index, team_ids, is_current)
            _load_box_scores(engine, summary, client, season, full, team_ids, game_ids)
            with engine.begin() as conn:
                index_ids = {player_ids[str(p["PERSON_ID"])] for p in index}
                _recompute_stints(conn, summary, season, is_current, index_ids)
    except Exception as exc:
        summary.outcome = "failed"
        summary.report = f"{type(exc).__name__}: {exc}"
        finish_run(
            engine, run_id, "failed", summary.total_inserted, summary.total_updated, summary.report
        )
        raise
    summary.outcome = "succeeded"
    finish_run(engine, run_id, "succeeded", summary.total_inserted, summary.total_updated)
    return summary
