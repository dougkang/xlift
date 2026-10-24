"""Reads a league's current matchup state (005, data-model.md)."""

from datetime import date

from sqlalchemy import text

from ffmodel.core.data.models import MATCHUP_STATS, MatchupLine, MatchupState


def get_matchup_state(conn, league_id: int) -> MatchupState | None:
    head = (
        conn.execute(
            text(
                "SELECT ms.week, ms.period_start, ms.period_end, ms.as_of, lr.finished_at"
                " FROM matchup_state ms LEFT JOIN load_run lr ON lr.run_id = ms.run_id"
                " WHERE ms.league_id = :l"
            ),
            {"l": league_id},
        )
        .mappings()
        .one_or_none()
    )
    if head is None:
        return None
    rows = conn.execute(
        text(
            f"SELECT fantasy_team_id, opponent_team_id, {', '.join(MATCHUP_STATS)}"
            " FROM matchup_team WHERE league_id = :l"
        ),
        {"l": league_id},
    ).mappings()
    lines = {
        r["fantasy_team_id"]: MatchupLine(
            team_id=r["fantasy_team_id"],
            opponent_id=r["opponent_team_id"],
            totals={s: int(r[s]) for s in MATCHUP_STATS},
        )
        for r in rows
    }
    return MatchupState(
        league_id=league_id,
        week=head["week"],
        period_start=date.fromisoformat(head["period_start"]),
        period_end=date.fromisoformat(head["period_end"]),
        as_of=date.fromisoformat(head["as_of"]),
        loaded_at=head["finished_at"],
        lines=lines,
    )
